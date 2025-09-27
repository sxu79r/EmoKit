from functools import partial
import os, shutil
import sys
import platform
import winreg  # 仅在 Windows 上有效
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QHBoxLayout, QStackedWidget, QInputDialog,
    QFileDialog, QApplication, QSystemTrayIcon, QMenu, QAction
    )
from qfluentwidgets import NavigationInterface, NavigationItemPosition, setTheme, Theme, \
    setThemeColor, MessageBox, InfoBar, InfoBarPosition, RoundMenu, Action, FluentIcon as FIF, \
    MenuAnimationType
from qframelesswindow import FramelessWindow

from .EmojiPage import EmojiPage
from .SettingsPage import SettingPage
from core.EmojiDB import EmojiDB, EMOJI_DIR
from core.LoadSettings import cfg
from .MainWindows_Interface import HotkeyListener, CustomTitleBar, AvatarWidget, AddEmojiGroupDialog


# ----------------- EmojiManager -----------------

class EmojiManager(FramelessWindow):
    def __init__(self):
        super().__init__()

        self.db = EmojiDB()
        self.pages = {}
        self.setAcceptDrops(True)

        self.edit_mode = False
        self.current_page = None
        self.all_nav_widgets = []
        self.current_nav_button = None

        self.init_window()
        self.init_ui()
        self.init_nav()

        self.switchTo(self.all_page)

        self.init_tray()
        self.hotkey_thread = HotkeyListener()
        if cfg.get(cfg.Hotkey):
            self.hotkey_thread.trigger.connect(self.show_window)
        self.hotkey_thread.start()

    # ---------------- 窗口属性 ----------------
    def init_window(self):
        self.setTitleBar(CustomTitleBar(self))
        self.setWindowTitle("EmoKit")
        self.setWindowIcon(QIcon('512.ico'))
        self.titleBar.setAttribute(Qt.WA_StyledBackground)
        self.resize(600, 500)
        setTheme(Theme.LIGHT)
        setThemeColor(cfg.get(cfg.ThemeColor))

    # ---------------- UI布局 ----------------
    def init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.nav = NavigationInterface(self, showMenuButton=True)
        self.main_layout.addWidget(self.nav, 1)

        # ---------------- 中间布局：右堆叠窗口 ----------------
        middle_layout = QHBoxLayout()
        middle_layout.setContentsMargins(0, 40, 0, 0)
        middle_layout.setSpacing(0)

        self.stackWidget = QStackedWidget(self)
        middle_layout.addWidget(self.stackWidget)
        self.nav.setExpandWidth(200)
        self.main_layout.addLayout(middle_layout)


    # ---------------- 导航栏按钮 ----------------

    def init_nav(self):
        # 顶部按钮
        self.nav.addItem("add_group", icon=FIF.ADD, text="添加分组",
                         onClick=self.add_group, position=NavigationItemPosition.TOP)
        self.nav.addItem("add_emoji", text="添加表情", icon=FIF.FOLDER_ADD,
                         onClick=lambda: self.add_emoji(), position=NavigationItemPosition.TOP)

        self.all_page = EmojiPage(0)
        self.pages[0] = self.all_page
        self.stackWidget.addWidget(self.all_page)
        self.nav.addItem("all", text="全部表情包", icon=FIF.VIEW,
                         onClick=partial(self.switchTo, self.all_page),
                         position=NavigationItemPosition.TOP)

        self.SettingsPage = SettingPage()
        self.SettingsPage.settings_changed.connect(self.apply_settings)
        self.SettingsPage.about_us_signal.connect(self.show_about_us)
        self.stackWidget.addWidget(self.SettingsPage)
        self.nav.addItem("settings", text="设置", icon=FIF.SETTING,
                         onClick=partial(self.switchTo, self.SettingsPage),
                         position=NavigationItemPosition.BOTTOM)

        self.load_groups()

    # ----------------- 拖拽事件 -----------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path) and path.lower().endswith((".png", ".jpg", ".bmp", ".gif")):
                self.add_emoji(path)
        for page in self.pages.values():
            page.load_emojis()

    # ----------------- 加载分组 -----------------
    def load_groups(self):
        groups = self.db.get_groups(exclude_zero=True)
        for gid, name, icon_path in groups:
            self._add_group_widget(gid, name, icon_path)

    # ---------------- 添加导航控件（加载已有分组时） ----------------

    def _add_group_widget(self, gid, name, icon_path=None):
        page = EmojiPage(gid)
        self.pages[gid] = page
        self.stackWidget.addWidget(page)

        avatar_widget = AvatarWidget(image_path=icon_path, text=name)
        avatar_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        avatar_widget.customContextMenuRequested.connect(
            partial(self.group_right_click, avatar_widget, gid)
            )

        avatar_widget.page = page

        self.all_nav_widgets.append(avatar_widget)

        def on_click():
            self.switchTo(page)

        self.nav.addWidget(f"group_{gid}", avatar_widget,
                           onClick=on_click,
                           position=NavigationItemPosition.SCROLL)

    def update_nav_selection(self, selected_widget):
        for widget in self.all_nav_widgets:
            widget.setSelected(False)
        selected_widget.setSelected(True)
        self.current_nav_button = selected_widget

    # ----------------- 删除分组安全逻辑 -----------------
    def safe_remove_group(self, widget, group_id):
        """逻辑删除导航控件，避免崩溃"""
        try:
            widget.setEnabled(False)
            widget.blockSignals(True)
            widget.hide()

            page = self.pages.pop(group_id, None)
            if page:
                self.stackWidget.removeWidget(page)

            self.db.move_emojis_to_group(group_id, 0)
            self.db.delete_group_only(group_id)

            if 0 in self.pages:
                self.pages[0].load_emojis()

        except Exception as e:
            w = MessageBox("错误", f"删除分组失败: {e}", self)
            w.exec()

    def search_emojis(self):
        """根据搜索框内容搜索表情"""
        keyword = self.search_box.text().strip()
        if not keyword:
            self.switchTo(self.all_page)
            return

        search_page = EmojiPage(-1)
        emojis = self.db.search_emojis(keyword)
        search_page.load_emojis_from_list(emojis)

        if hasattr(self, "_search_page"):
            self.stackWidget.removeWidget(self._search_page)
        self._search_page = search_page
        self.stackWidget.addWidget(search_page)
        self.stackWidget.setCurrentWidget(search_page)

    # ----------------- 右键菜单（Fluent 风格） -----------------
    def group_right_click(self, widget, group_id, pos):

        menu = RoundMenu(parent=self)

        rename_action = Action(FIF.EDIT, "修改名称")
        change_icon_action = Action(FIF.FOLDER, "修改图标")
        delete_action = Action(FIF.DELETE, "删除分组")
        menu.addActions([rename_action, change_icon_action, delete_action])

        menu.exec(widget.mapToGlobal(pos), aniType=MenuAnimationType.DROP_DOWN)

        rename_action.triggered.connect(lambda: self._rename_group(widget, group_id))
        change_icon_action.triggered.connect(lambda: self._change_group_icon(widget, group_id))
        delete_action.triggered.connect(lambda: self._delete_group(widget, group_id))

    # ----------------- 辅助方法 -----------------
    def _rename_group(self, widget, group_id):
        new_name, ok = QInputDialog.getText(self, "修改分组名称", "名称：", text=widget.text)
        if ok and new_name.strip():
            widget.text = new_name.strip()
            widget.update()
            self.db.update_group_name(group_id, widget.text)

    def _change_group_icon(self, widget, group_id):
        path, _ = QFileDialog.getOpenFileName(self, "选择分组图标", "",
                                              "Images (*.png *.jpg *.bmp *.gif)")
        if path:
            widget.setAvatar(path)
            self.db.update_group_icon(group_id, path)

    def _delete_group(self, widget, group_id):
        reply = MessageBox(
            "删除分组",
            f"确认删除分组“{widget.text}”？\n此操作无法撤销，但分组下的表情会移动到“未分组”。",
            self
            )
        if reply.exec():
            self.safe_remove_group(widget, group_id)

    # ---------------- 编辑模式 ----------------
    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        # 同步当前页面
        if hasattr(self, 'current_page') and self.current_page:
            if hasattr(self.current_page, "set_edit_mode"):
                self.current_page.set_edit_mode(self.edit_mode)

    def switchTo(self, page):
        """切换页面并更新导航栏选中效果"""
        self.stackWidget.setCurrentWidget(page)

        if hasattr(page, "load_emojis"):
            page.load_emojis()
            if getattr(self, 'edit_mode', False):
                page.set_edit_mode(True)

        # 🔹 更新导航栏选中效果
        for widget in self.all_nav_widgets:
            if widget.page == page:
                widget.setSelected(True)
                self.current_nav_button = widget
            else:
                widget.setSelected(False)
            widget.update()

        self.current_page = page

        # ---------------- 添加分组 ----------------

    def add_group(self):
        dialog = AddEmojiGroupDialog("请输入名称..", self)
        if dialog.exec():
            group_name = dialog.get_text().strip()
            existing_groups = self.db.get_groups_simple()  # [(id, name), ...]
            if group_name in [name for _, name in existing_groups]:
                w = MessageBox("分组已存在", f"分组“{group_name}”已存在，请输入其他名称。", self)
                w.exec()
                return
        else:
            return

        gid = self.db.add_group(group_name)

        page = EmojiPage(gid)
        self.pages[gid] = page
        self.stackWidget.addWidget(page)

        avatar_widget = AvatarWidget(text=group_name, page=page)
        avatar_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        avatar_widget.customContextMenuRequested.connect(
            partial(self.group_right_click, avatar_widget, gid)
            )

        self.nav.addWidget(
            f"group_{gid}",
            avatar_widget,
            onClick=partial(self.switchTo, page),
            position=NavigationItemPosition.SCROLL
            )

        self.all_nav_widgets.append(avatar_widget)

        self.switchTo(page)
        self.update_nav_selection(avatar_widget)

    # ------添加表情-----
    def add_emoji(self, file_path=None):
        try:
            if not file_path:
                file_path, _ = QFileDialog.getOpenFileName(
                    self, "选择表情图片", "", "Images (*.png *.jpg *.bmp *.gif)")
                if not file_path:
                    return

            tag = os.path.basename(file_path)
            group_id = 0

            os.makedirs(EMOJI_DIR, exist_ok=True)
            filename = os.path.basename(file_path)
            dest_path = os.path.join(EMOJI_DIR, filename)
            count = 1
            while os.path.exists(dest_path):
                name, ext = os.path.splitext(filename)
                dest_path = os.path.join(EMOJI_DIR, f"{name}_{count}{ext}")
                count += 1

            shutil.copy(file_path, dest_path)

            eid = self.db.add_emoji(dest_path, tag, group_id)

            if group_id != 0:
                page = self.pages[group_id]
                page.add_emoji_to_page(dest_path, tag, eid)

            self.pages[0].add_emoji_to_page(dest_path, tag, eid)

        except Exception as e:
            MessageBox("错误", f"添加表情时出错：{str(e)}", self).exec()




        except Exception as e:
            MessageBox("错误", f"添加表情时出错：{str(e)}", self).exec()

    def apply_settings(self, key, value):
        if key == "ThemeColor":
            self.apply_theme_color(value)
        elif key == "Automatic_Startup":
            self.set_autostart(value)
        self.settings_saved()

    def apply_theme_color(self, color):
        """立即更新主题颜色"""
        setThemeColor(color)

    def set_autostart(self, enable: bool):
        """设置开机自启"""
        app_path = sys.executable
        app_name = "EmoKit"

        if platform.system() == "Windows":
            # Windows 注册表方式
            try:
                reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_ALL_ACCESS) as key:
                    if enable:
                        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{app_path}"')
                    else:
                        try:
                            winreg.DeleteValue(key, app_name)
                        except FileNotFoundError:
                            pass
            except Exception as e:
                MessageBox("错误", f"设置开机自启失败: {e}", self).exec()

        elif platform.system() == "Darwin":
            # macOS 使用 LaunchAgents
            plist_path = os.path.expanduser(f"~/Library/LaunchAgents/{app_name}.plist")
            if enable:
                plist_content = f"""
                <?xml version="1.0" encoding="UTF-8"?>
                <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
                "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
                <plist version="1.0">
                <dict>
                    <key>Label</key>
                    <string>{app_name}</string>
                    <key>ProgramArguments</key>
                    <array>
                        <string>{app_path}</string>
                    </array>
                    <key>RunAtLoad</key>
                    <true/>
                </dict>
                </plist>
                """
                with open(plist_path, "w") as f:
                    f.write(plist_content)
            else:
                if os.path.exists(plist_path):
                    os.remove(plist_path)

    def settings_saved(self):
        InfoBar.success(
            title='保存成功',
            content='设置已生效',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2000,
            parent=self
            )

    def show_about_us(self):
        """显示关于我们窗口"""
        w = MessageBox(
            "关于我们",
            "作者：雀玖r\n"
            "联系方式：sxu79r@163.com\n"
            f"当前版本:{cfg.get(cfg.Vision)}\n"
            "感谢您的使用！", self
            )
        w.exec()

    # -----后台运行-----

    def show_window(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(QIcon("512.ico"), self)
        tray_menu = QMenu()

        restore_action = QAction("打开", self)
        restore_action.triggered.connect(self.showNormal)
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(QApplication.instance().quit)

        tray_menu.addAction(restore_action)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_activated)

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.showNormal()
            self.activateWindow()

    def closeEvent(self, event):
        if cfg.get(cfg.Tray_State):
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "表情包管理器",
                "程序已最小化到托盘，双击图标可恢复",
                QSystemTrayIcon.Information,
                2000
                )
        else:
            w = MessageBox(
                "退出确认",
                "你想要退出程序还是最小化到托盘？",
                self
                )

            w.yesButton.setText("退出程序")
            w.cancelButton.setText("最小化到托盘")

            if w.exec():
                event.accept()
                QApplication.instance().quit()
            else:
                event.ignore()
                self.hide()
                self.tray_icon.showMessage(
                    "表情包管理器",
                    "程序已最小化到托盘，双击图标可恢复",
                    QSystemTrayIcon.Information,
                    2000
                    )
