from PyQt5.QtGui import QIcon, QPainter, QImage, QBrush, QColor, QFont
from PyQt5.QtCore import Qt, QRect, QThread, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget
import keyboard
from qfluentwidgets import FluentIcon as FIF, PrimaryPushButton, SearchLineEdit, MessageBoxBase, \
    SubtitleLabel, LineEdit, \
    CaptionLabel, NavigationWidget
from qframelesswindow import TitleBar
from .EmojiPage import EmojiPage
from core.LoadSettings import cfg


class AddEmojiGroupDialog(MessageBoxBase):
    """Fluent 风格的重命名表情对话框"""

    def __init__(self, old_name="", parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("添加分组", self)
        self.inputLineEdit = LineEdit(self)
        self.inputLineEdit.setPlaceholderText(old_name)
        self.inputLineEdit.setClearButtonEnabled(True)

        self.warningLabel = CaptionLabel("名称不能为空")
        self.warningLabel.setTextColor("#cf1010", QColor(255, 28, 32))
        self.warningLabel.hide()

        # 将控件加入布局
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.inputLineEdit)
        self.viewLayout.addWidget(self.warningLabel)

        # 修改按钮文本
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")

        self.widget.setMinimumWidth(350)

    def validate(self):
        """验证输入是否合法"""
        text = self.inputLineEdit.text().strip()
        isValid = bool(text)
        self.warningLabel.setHidden(isValid)
        self.inputLineEdit.setError(not isValid)
        return isValid

    def get_text(self):
        return self.inputLineEdit.text().strip()



class HotkeyListener(QThread):
    trigger = pyqtSignal()

    def __init__(self, hotkey="ctrl+shift+e"):
        super().__init__()
        self.current_hotkey = hotkey

    def run(self):
        # 初次监听
        keyboard.add_hotkey(self.current_hotkey, lambda: self.trigger.emit())
        keyboard.wait()


class AvatarWidget(NavigationWidget):
    def __init__(self, image_path=None, text='', parent=None, page=None):
        super().__init__(isSelectable=False, parent=parent)  # 必须传 isSelectable
        self.text = f'分组:{text}'
        self.avatar_path = image_path or ''
        self.avatar = QImage(self.avatar_path).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.selected = False
        self.page = page

    def setAvatar(self, path):
        self.avatar_path = path
        self.avatar = QImage(path).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.update()

    def setSelected(self, selected: bool):
        self.selected = selected
        self.update()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.SmoothPixmapTransform | QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        if getattr(self, 'selected', False):
            painter.setBrush(QColor(230, 230, 230))
            painter.drawRoundedRect(self.rect(), 5, 5)
            bar_width = 3
            bar_color = QColor(164, 170, 255)
            radius = 2
            painter.setBrush(bar_color)
            painter.drawRoundedRect(0, 10, bar_width, self.height() - 20, radius, radius)

        if getattr(self, 'isEnter', False):
            painter.setBrush(QColor(255, 255, 255, 30))
            painter.drawRoundedRect(self.rect(), 5, 5)

        painter.setBrush(QBrush(self.avatar))
        painter.translate(8, 6)
        painter.drawEllipse(0, 0, self.avatar.width(), self.avatar.height())
        painter.translate(-8, -6)

        if not getattr(self, 'isCompacted', False):
            painter.setPen(Qt.black)
            font = QFont('Microsoft YaHei')
            font.setPixelSize(12)
            painter.setFont(font)
            painter.drawText(QRect(64, 0, 255, 36), Qt.AlignVCenter, self.text)


# ---------------- 自定义标题栏 ----------------
class CustomTitleBar(TitleBar):
    """带图标、标题、搜索框和编辑模式按钮的自定义标题栏"""

    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedHeight(40)

        self.hBoxLayout.removeWidget(self.minBtn)
        self.hBoxLayout.removeWidget(self.maxBtn)
        self.hBoxLayout.removeWidget(self.closeBtn)

        self.iconLabel = QLabel(self)
        self.iconLabel.setFixedSize(24, 24)
        self.hBoxLayout.insertSpacing(0, 40)
        self.hBoxLayout.insertWidget(1, self.iconLabel, 0, Qt.AlignLeft | Qt.AlignVCenter)
        self.window().windowIconChanged.connect(self.setIcon)

        self.titleLabel = QLabel(self)
        self.hBoxLayout.insertWidget(2, self.titleLabel, 0, Qt.AlignLeft | Qt.AlignVCenter)
        self.titleLabel.setObjectName('titleLabel')
        self.window().windowTitleChanged.connect(self.setTitle)

        self.searchLineEdit = SearchLineEdit(self)
        self.searchLineEdit.setPlaceholderText('搜索组内表情包...')
        self.searchLineEdit.setFixedSize(210, 30)
        self.searchLineEdit.setClearButtonEnabled(True)
        self.searchLineEdit.textChanged.connect(self.on_search_text_changed)

        self.editModeBtn = PrimaryPushButton("编辑", self)
        self.editModeBtn.setIcon(FIF.PENCIL_INK)
        self.editModeBtn.setCheckable(True)
        self.editModeBtn.setFixedSize(80, 30)
        self.editModeBtn.clicked.connect(self.on_edit_mode_toggled)

        # ---------------- 中间居中布局 ----------------
        centerLayout = QHBoxLayout()
        centerLayout.setSpacing(25)
        centerLayout.setContentsMargins(0, 0, 0, 0)
        centerLayout.addWidget(self.searchLineEdit)
        centerLayout.addWidget(self.editModeBtn)
        self.centerWidget = QWidget(self)
        self.centerWidget.setLayout(centerLayout)
        self.centerWidget.setFixedHeight(40)
        self.hBoxLayout.addWidget(self.centerWidget, 0, Qt.AlignCenter)

        # ---------------- 右侧窗口控制按钮 ----------------
        self.rightButtonLayout = QHBoxLayout()
        self.rightButtonLayout.setSpacing(0)
        self.rightButtonLayout.setContentsMargins(0, 0, 0, 0)
        self.rightButtonLayout.addWidget(self.minBtn)
        self.rightButtonLayout.addWidget(self.maxBtn)
        self.rightButtonLayout.addWidget(self.closeBtn)
        self.hBoxLayout.addLayout(self.rightButtonLayout, 0)

    def setTitle(self, title):
        self.titleLabel.setText(title)
        self.titleLabel.setStyleSheet("font: 9pt '微软雅黑';")
        self.titleLabel.adjustSize()

    def setIcon(self, icon):
        self.iconLabel.setPixmap(QIcon(icon).pixmap(24, 24))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        container_width = self.centerWidget.width()
        container_height = self.centerWidget.height()
        new_x = (self.width() - container_width) // 2
        new_y = (self.height() - container_height) // 2
        self.centerWidget.move(new_x, new_y)

    def on_search_text_changed(self, text: str):
        parent = self.parent()
        if parent and hasattr(parent, "stackWidget"):
            current_page = parent.stackWidget.currentWidget()
            if isinstance(current_page, EmojiPage):
                if text.strip():
                    current_page.search_and_display(text)
                else:
                    current_page.load_emojis()

    def on_edit_mode_toggled(self, checked: bool):
        parent = self.parent()
        if parent:
            parent.edit_mode = checked
            for page in parent.pages.values():
                page.set_edit_mode(checked)
