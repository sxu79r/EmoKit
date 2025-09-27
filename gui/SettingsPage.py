from qfluentwidgets import SwitchSettingCard, ColorSettingCard
import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import (
    ScrollArea, SettingCardGroup, PushSettingCard, InfoBar, InfoBarPosition,
    PrimaryPushSettingCard, FluentIcon as FIF,
    )
from PyQt5.QtCore import Qt, pyqtSignal, QUrl
from PyQt5.QtGui import QDesktopServices

from core.LoadSettings import cfg


class SettingPage(ScrollArea):
    about_us_signal = pyqtSignal()
    settings_changed = pyqtSignal(str, object)
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setFrameShape(self.NoFrame)
        self.setFrameShadow(self.Plain)
        self.setStyleSheet("border: none; background-color: rgba(230,230,230);")

        self.scrollWidget = QWidget()
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)

        self.vbox = QVBoxLayout(self.scrollWidget)

        self.vbox.setContentsMargins(20, 0, 20, 20)
        self.vbox.setSpacing(10)
        self.__initPathSettings()
        self.__initWindowSettings()
        self.__initUpdateSettings()
        cfg.ThemeColor.valueChanged.connect(
            lambda color: self.settings_changed.emit("ThemeColor", color)
        )
        cfg.Automatic_Startup.valueChanged.connect(
            lambda state: self.settings_changed.emit("Automatic_Startup", state)
        )
        cfg.Tray_State.valueChanged.connect(
            lambda state: self.settings_changed.emit("Tray_State", state)
        )
        cfg.Hotkey.valueChanged.connect(
            lambda state: self.settings_changed.emit("Hotkey", state)
        )

    # -----------------------------
    # 路径设置
    # -----------------------------
    def __initPathSettings(self):
        pathGroup = SettingCardGroup("路径设置", self.scrollWidget)

        self.emojiPathCard = PushSettingCard(
            "表情保存路径",
            FIF.SAVE_AS,
            "点击打开所在目录",
            cfg.EmojiSaved_Path.value,
            parent=pathGroup
            )

        self.emojiPathCard.clicked.connect(self.__openEmojiPath)

        self.dbPathCard = PushSettingCard(
            "数据库路径",
            FIF.FOLDER,
            "点击打开所在目录",
            cfg.get(cfg.EmojiDB_Path),
            parent=pathGroup
            )
        self.dbPathCard.clicked.connect(self.__openDBPath)

        pathGroup.addSettingCard(self.emojiPathCard)
        pathGroup.addSettingCard(self.dbPathCard)
        self.vbox.addWidget(pathGroup)

    def __openEmojiPath(self):
        path = cfg.get(cfg.EmojiSaved_Path)
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            self.settings_failed("表情保存路径不存在")

    def __openDBPath(self):
        db_path = cfg.get(cfg.EmojiDB_Path)
        folder = os.path.dirname(db_path)
        if os.path.exists(folder):
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        else:
            self.settings_failed("数据库目录不存在")

    def settings_failed(self, msg: str):
        InfoBar.error(
            title='操作失败',
            content=msg,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
            parent=self.scrollWidget
            )
    # -----------------------------
    # 窗口设置
    # -----------------------------
    def __initWindowSettings(self):
        windowGroup = SettingCardGroup("窗口设置", self.scrollWidget)

        self.trayCard = SwitchSettingCard(
            FIF.APPLICATION,
            "启用托盘",
            "是否最小化到托盘",
            configItem=cfg.Tray_State,
            parent=windowGroup
            )

        self.startupCard = SwitchSettingCard(
            FIF.POWER_BUTTON,
            "开机自启",
            "开机时自动启动",
            configItem=cfg.Automatic_Startup,
            parent=windowGroup
            )

        self.themeColorCard = ColorSettingCard(
            cfg.ThemeColor,
            FIF.BRUSH,
            "主题颜色",
            "自定义界面主题颜色",
            parent=windowGroup
            )

        self.hotkeyCard = SwitchSettingCard(
            FIF.UNIT,
            "启用窗口快捷键",
            f"快捷键: Shift+Ctrl+E",
            configItem=cfg.Hotkey,
            parent=windowGroup
            )

        windowGroup.addSettingCard(self.hotkeyCard)

        windowGroup.addSettingCard(self.trayCard)
        windowGroup.addSettingCard(self.startupCard)
        windowGroup.addSettingCard(self.themeColorCard)
        self.vbox.addWidget(windowGroup)

    def __initUpdateSettings(self):
        aboutGroup = SettingCardGroup("反馈", self.scrollWidget)
        self.feedbackCard = PrimaryPushSettingCard(
            '提供反馈',
            FIF.FEEDBACK,
            '提供反馈',
            '诉说你遇到的问题，帮助我们改善优化项目',
            aboutGroup
            )
        self.about_card = PrimaryPushSettingCard(
            "关于我们",
            FIF.INFO,
            "点击查看作者信息",
            "关于我们",
            parent=aboutGroup
            )

        aboutGroup.addSettingCard(self.about_card)
        aboutGroup.addSettingCard(self.feedbackCard)
        self.about_card.clicked.connect(self.show_about_us)
        self.feedbackCard.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl('https://github.com/sxu79r/EmoKit/issues')))
        self.vbox.addWidget(aboutGroup)

    def show_about_us(self):
        """显示关于我们窗口"""
        self.about_us_signal.emit()

