import os
import sqlite3
from .LoadSettings import cfg
DB_PATH = cfg.get(cfg.EmojiDB_Path)
EMOJI_DIR = cfg.get(cfg.EmojiSaved_Path)


# ----------------- 初始化数据库 -----------------
class EmojiDB():
    def __init__(self):
        self.db_path = DB_PATH
        os.makedirs(EMOJI_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS emojis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT NOT NULL,
            tags TEXT,
            group_id INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            icon_path TEXT DEFAULT ''
        )''')
        c.execute("INSERT OR IGNORE INTO groups (id, name) VALUES (0, '未分组')")
        conn.commit()
        conn.close()

        self._cleanup_invalid_emojis()

    def _cleanup_invalid_emojis(self):
        """删除数据库中丢失文件的表情记录"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, image_path FROM emojis")
        rows = c.fetchall()
        removed = 0
        for eid, path in rows:
            if not os.path.exists(path):
                c.execute("DELETE FROM emojis WHERE id=?", (eid,))
                removed += 1
        if removed > 0:
            print(f"⚠️ 已清理 {removed} 条失效的表情记录")
        conn.commit()
        conn.close()

    def get_emojis(self, group_id=0):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        if group_id == 0:
            c.execute("SELECT id, image_path, tags FROM emojis")
        else:
            c.execute("SELECT id, image_path, tags FROM emojis WHERE group_id=?", (group_id,))
        result = c.fetchall()
        conn.close()
        return result

    def get_image_path(self, eid):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT image_path FROM emojis WHERE id=?", (eid,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else None

    def get_groups(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, name FROM groups")
        groups = c.fetchall()
        conn.close()
        return groups

    def update_emoji_group(self, eid, group_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE emojis SET group_id=? WHERE id=?", (group_id, eid))
        conn.commit()
        conn.close()

    def delete_emoji(self, eid):
        """删除表情：数据库记录 + 本地文件"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()


            c.execute("SELECT image_path FROM emojis WHERE id=?", (eid,))
            row = c.fetchone()
            path = row[0] if row else None

            c.execute("DELETE FROM emojis WHERE id=?", (eid,))
            conn.commit()
            conn.close()


            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"删除本地文件失败: {e}")

        except Exception as e:
            print(f"删除表情包失败: {e}")

    # ----------------- 分组相关 -----------------
    def get_groups(self, exclude_zero=False):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        if exclude_zero:
            c.execute("SELECT id, name, icon_path FROM groups WHERE id != 0")
        else:
            c.execute("SELECT id, name, icon_path FROM groups")
        groups = c.fetchall()
        conn.close()
        return groups

    def add_group(self, name):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO groups (name) VALUES (?)", (name,))
        conn.commit()
        gid = c.lastrowid
        conn.close()
        return gid

    def update_group_name(self, group_id, new_name):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE groups SET name=? WHERE id=?", (new_name, group_id))
        conn.commit()
        conn.close()

    def update_group_icon(self, group_id, icon_path):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE groups SET icon_path=? WHERE id=?", (icon_path, group_id))
        conn.commit()
        conn.close()

    # ----------------- 表情相关 -----------------
    def get_groups_simple(self):
        """仅返回 id 和 name，用于选择分组"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, name FROM groups")
        groups = c.fetchall()
        conn.close()
        return groups

    def add_emoji(self, image_path, tags, group_id=0):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO emojis (image_path, tags, group_id) VALUES (?,?,?)",
            (image_path, tags, group_id),
            )
        conn.commit()
        eid = c.lastrowid
        conn.close()
        return eid

    def move_emojis_to_group(self, old_group_id, new_group_id):
        """将表情从 old_group_id 移动到 new_group_id"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE emojis SET group_id=? WHERE group_id=?", (new_group_id, old_group_id))
        conn.commit()
        conn.close()

    def update_emoji_name(self, eid, new_name):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE emojis SET tags=? WHERE id=?", (new_name, eid))
        conn.commit()
        conn.close()

    def delete_group_only(self, group_id):
        """只删除分组，不删除表情"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM groups WHERE id=?", (group_id,))
        conn.commit()
        conn.close()

    def search_emojis(self, keyword, group_id=None):
        """
        搜索表情，group_id=None 表示全部分组，0 表示未分组
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        like = f"%{keyword}%"

        if group_id is None:
            # 全部分组
            c.execute("""
                SELECT id, image_path, tags, group_id, created_at
                FROM emojis
                WHERE tags LIKE ?
                ORDER BY created_at DESC
            """, (like,))
        elif group_id == 0:
            # 未分组
            c.execute("""
                SELECT id, image_path, tags, group_id, created_at
                FROM emojis
                WHERE (tags LIKE ?) AND group_id = 0
                ORDER BY created_at DESC
            """, (like,))
        else:
            # 指定分组
            c.execute("""
                SELECT id, image_path, tags, group_id, created_at
                FROM emojis
                WHERE (tags LIKE ?) AND group_id = ?
                ORDER BY created_at DESC
            """, (like, group_id))

        results = c.fetchall()
        conn.close()
        return results
