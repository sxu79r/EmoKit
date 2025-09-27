from PyQt5.QtCore import QTimer
from qfluentwidgets import RoundMenu, Action, MenuAnimationType, FluentIcon as FIF
from functools import partial
from qfluentwidgets import StateToolTip, ScrollBar
from PyQt5.QtGui import QDrag, QPixmap, QMouseEvent, QPainter
from PyQt5.QtCore import Qt, QMimeData, QPoint
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QMenu, QApplication
from PyQt5.QtGui import QPixmap, QMovie, QPainter, QPen, QColor, QFont, QImage
from PyQt5.QtCore import Qt, QSize, QEvent, QMimeData, QUrl
import tempfile, shutil, os
from functools import partial
from core.EmojiDB import EmojiDB
from core.LoadSettings import cfg
from .EmojiPage_Interface import EmojiItemWidget, RenameEmojiDialog, EmojiListWidget, DeleteArea



class EmojiPage(QWidget):
    """表情页，支持高 DPI 渲染、点击选中、右键菜单"""

    def __init__(self, group_id):
        super().__init__()
        self.group_id = group_id
        self.db = EmojiDB()

        self.state_tooltip = None  # 初始化状态提示

        self.list_widget = EmojiListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setFlow(QListWidget.LeftToRight)

        # 允许拖动
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setMovement(QListWidget.Free)
        self.list_widget.setDragEnabled(False)  # 允许拖动
        self.list_widget.setAcceptDrops(True)  # 允许放置
        self.list_widget.setDropIndicatorShown(True)  # 显示放置指示线
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        self.list_widget.setDragDropMode(QListWidget.DragDrop)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        # 保持手动 QDrag
        self.list_widget.setDefaultDropAction(Qt.MoveAction)

        QTimer.singleShot(0, lambda: self.list_widget.setFlow(QListWidget.LeftToRight))
        self.list_widget.setIconSize(QSize(80, 80))
        self.list_widget.setGridSize(QSize(80, 100))
        self.list_widget.setWordWrap(True)
        self.list_widget.setSpacing(10)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.itemClicked.connect(self.clear_selection)
        self.list_widget.itemDoubleClicked.connect(self.copy_to_clipboard)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)

        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # 删除区域（初始隐藏）
        self.delete_area = DeleteArea(self)
        self.delete_area.setVisible(False)
        layout.addWidget(self.delete_area)

        self.setStyleSheet("""
            background-color: rgba(	230, 230, 230);
        """)
        self.edit_mode = False

    def load_emojis(self):
        self.list_widget.clear()
        emojis = self.db.get_emojis(self.group_id)
        for eid, path, tags in emojis:
            display_name = tags if len(tags) <= 10 else tags[:10] + "..."
            widget = EmojiItemWidget(path, text=display_name, size=80)
            item = QListWidgetItem()
            item.setSizeHint(QSize(80, 80))
            item.setData(Qt.UserRole, eid)  # 数据 ID
            item.setData(Qt.UserRole + 1, widget)  # 保存 Widget
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            if self.edit_mode:
                self.refresh_edit_mode()

    def add_emoji_to_page(self, path, tag, eid):
        lw = self.list_widget
        lw.setUpdatesEnabled(False)  # 暂停重绘
        scroll_pos = lw.verticalScrollBar().value()  # 保存滚动位置

        display_name = tag if len(tag) <= 10 else tag[:10] + "..."
        widget = EmojiItemWidget(path, text=display_name, size=80)
        item = QListWidgetItem()
        item.setSizeHint(QSize(80, 80))
        item.setData(Qt.UserRole, eid)
        item.setData(Qt.UserRole + 1, widget)
        lw.addItem(item)
        lw.setItemWidget(item, widget)

        if self.edit_mode:
            widget.text_label.setVisible(True)

        lw.setUpdatesEnabled(True)  # 恢复重绘
        QTimer.singleShot(0, lambda: lw.verticalScrollBar().setValue(scroll_pos))

    def set_edit_mode(self, enabled: bool):
        """切换编辑模式"""
        self.edit_mode = enabled

        # 延迟创建 StateToolTip，保证每个页面只创建一次
        if enabled:
            if not self.state_tooltip:
                self.state_tooltip = StateToolTip('编辑模式', '当前处于编辑模式，可以删除或重命名表情', self)
                # 延迟应用样式
                QTimer.singleShot(0, lambda: self.state_tooltip.setStyleSheet("""
                    QWidget {
                        background-color: rgba(247, 180, 180);
                        color: black;
                        font-family: "微软雅黑";
                    }
                """))
            else:
                self.state_tooltip.setTitle('编辑模式')
                self.state_tooltip.setContent('当前处于编辑模式，可以删除或重命名表情')
                QTimer.singleShot(0, lambda: self.state_tooltip.setStyleSheet("""
                    QWidget {
                        background-color: rgba(247, 180, 180);
                        color: black;
                        font-family: "微软雅黑";
                    }
                """))

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget:
                widget.text_label.setVisible(enabled)

        # 删除区域显示/隐藏
        self.delete_area.setVisible(enabled)
        # 拖拽功能
        self.list_widget.setDragEnabled(enabled)

        # 状态提示显示
        if enabled and self.state_tooltip:
            margin = 20
            x = self.width() - self.state_tooltip.width() - margin
            y = self.height() - self.state_tooltip.height() - 80
            self.state_tooltip.move(x, y)
            self.state_tooltip.setVisible(True)
            self.state_tooltip.show()
        elif self.state_tooltip:
            self.state_tooltip.setVisible(False)

    def resizeEvent(self, event):
        """编辑模式下，动态调整状态提示位置"""
        super().resizeEvent(event)
        if self.edit_mode and self.state_tooltip and self.state_tooltip.isVisible():
            margin = 20
            x = self.width() - self.state_tooltip.width() - margin
            y = self.height() - self.state_tooltip.height() - margin
            self.state_tooltip.move(x, y)

    def search_and_display(self, keyword: str):
        """根据关键词搜索表情"""
        self.list_widget.clear()
        results = self.db.search_emojis(keyword, self.group_id if self.group_id != 0 else None)
        for eid, path, tags, gid, created_at in results:
            display_name = tags if len(tags) <= 10 else tags[:10] + "..."
            widget = EmojiItemWidget(path, text=display_name, size=80)
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.UserRole, eid)
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

    def clear_selection(self):
        """清除所有选中状态"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget and hasattr(widget, "setSelected"):
                widget.setSelected(False)

    def copy_to_clipboard(self, item):
        eid = item.data(Qt.UserRole)
        path = self.db.get_image_path(eid)
        if not path or not os.path.exists(path):
            return
        clipboard = QApplication.clipboard()
        if path.lower().endswith(".gif"):
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, os.path.basename(path))
            shutil.copy(path, temp_path)
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(temp_path)])
            clipboard.setMimeData(mime)
        else:
            clipboard.setPixmap(QPixmap(path))

    def show_context_menu(self, pos):
        lw = self.list_widget
        item = lw.itemAt(pos)
        if not item:
            return

        # 创建 Fluent 风格菜单
        menu = RoundMenu(parent=self)

        # 添加操作
        rename_action = Action(FIF.EDIT, "更改名称")
        delete_action = Action(FIF.DELETE, "删除表情")
        menu.addActions([rename_action, delete_action])

        # 添加分组子菜单
        groups_menu = RoundMenu("设置分组", self)
        groups_menu.setIcon(FIF.PEOPLE)
        groups = self.db.get_groups()
        for gid, name, icon_path in groups:
            group_action = Action(FIF.HEART, name)  # 可自定义图标
            group_action.triggered.connect(partial(self.set_emoji_group, item, gid))
            groups_menu.addAction(group_action)
        menu.addMenu(groups_menu)

        # 绑定点击事件
        rename_action.triggered.connect(lambda: self.rename_emoji(item))
        delete_action.triggered.connect(lambda: self.delete_emoji(item))

        # 弹出菜单
        menu.exec(lw.mapToGlobal(pos), aniType=MenuAnimationType.DROP_DOWN)

    def rename_emoji(self, item):
        eid = item.data(Qt.UserRole)
        widget = self.list_widget.itemWidget(item)
        old_name = widget.text_label.text() if widget else ""

        dialog = RenameEmojiDialog(old_name, self)
        if dialog.exec():
            new_name = dialog.get_text()
            if new_name:
                self.db.update_emoji_name(eid, new_name)
                if widget:
                    widget.text_label.setText(new_name)

    def set_emoji_group(self, item, group_id):
        """设置表情的分组（只更新当前 item，不刷新整个页面）"""
        eid = item.data(Qt.UserRole)
        self.db.update_emoji_group(eid, group_id)
        # ✅ 不再调用 load_emojis()，避免整个页面刷新
        widget = self.list_widget.itemWidget(item)
        if widget:
            # 可以给 widget 做个标记，比如加个分组角标（如果你需要）
            widget.update()

    def delete_emoji(self, item):
        """删除表情（只移除当前项，不刷新整个页面）"""
        widget = self.list_widget.itemWidget(item)
        if widget:
            widget.stop_movie()  # 停止 GIF 播放

        eid = item.data(Qt.UserRole)
        path = self.db.get_image_path(eid)
        self.db.delete_emoji(eid)

        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print("删除本地文件失败:", e)

        # ✅ 只移除当前 item，不刷新整个页面
        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)

        # ✅ 保持编辑模式的名字显示状态
        self.refresh_edit_mode()

    def refresh_edit_mode(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget:
                widget.text_label.setVisible(self.edit_mode)
