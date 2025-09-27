from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QDrag, QPixmap, QMovie, QPainter, QPen, QColor, QImage
from PyQt5.QtCore import Qt, QMimeData, QPoint
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QApplication
from qfluentwidgets import MessageBoxBase, SubtitleLabel, LineEdit, CaptionLabel
import tempfile, shutil, os

from core.EmojiDB import EmojiDB

class RenameEmojiDialog(MessageBoxBase):
    """Fluent 风格的重命名表情对话框"""

    def __init__(self, old_name="", parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("更改名称", self)
        self.inputLineEdit = LineEdit(self)
        self.inputLineEdit.setText(old_name)  # 设置初始文本
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


class EmojiListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.InternalMove)  # 内部拖动管理 item
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDropIndicatorShown(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.pos() - self.start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        item = self.itemAt(self.start_pos)
        if not item:
            return
        widget = self.itemWidget(item)
        if not widget:
            return

        # QDrag 仅用于显示拖动效果
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(widget.path)
        drag.setMimeData(mime)

        pixmap = widget.label.pixmap()
        if pixmap:
            drag.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        drag.exec_(Qt.MoveAction)


# -----删除拖拽区域-----
class DeleteArea(QLabel):
    def __init__(self, parent=None):
        super().__init__("拖到这里删除", parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: rgba(255,0,0,0.2); border: 2px dashed red;")
        self.setFixedHeight(60)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        # 接受文本或 QListWidget 内部数据
        if event.mimeData().hasText() or event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText() or event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not event.mimeData().hasText():
            event.ignore()
            return

        path = event.mimeData().text()
        parent_page = self.parent()
        if not parent_page:
            event.ignore()
            return

        # 遍历列表找到 item
        for i in range(parent_page.list_widget.count()):
            item = parent_page.list_widget.item(i)
            widget = parent_page.list_widget.itemWidget(item)
            if widget and widget.path == path:
                parent_page.delete_emoji(item)
                break

        event.acceptProposedAction()


class EmojiItemWidget(QWidget):
    def __init__(self, path, text='', size=80):
        super().__init__()
        self.path = path
        self.base_size = size
        self.is_gif = path.lower().endswith(".gif")
        self.movie = None
        self.selected = False

        self.dpr = self.devicePixelRatioF()
        self.size = int(self.base_size * self.dpr)
        self.start_pos = None  # 记录鼠标按下位置
        self.label = QLabel()
        self.label.setFixedSize(self.base_size, self.base_size)
        self.label.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(80, 100)  # 图片80 + 文字30 + 间距5~10
        self.setMaximumSize(80, 100)
        # 名称控件
        self.text_label = QLabel(text)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setStyleSheet("color: black; font-size: 10pt;font-family: '微软雅黑';")
        self.text_label.setWordWrap(True)  # 防止文字太长溢出
        self.text_label.setFixedHeight(20)  # 保证有空间显示
        self.text_label.setVisible(False)  # 默认编辑模式隐藏

        # 垂直布局：图片在上，名称在下
        layout = QVBoxLayout(self)
        layout.addWidget(self.label, alignment=Qt.AlignCenter)
        layout.addWidget(self.text_label, alignment=Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.load_image(self.path)

        # **启用鼠标跟踪，无论是否 GIF**
        self.setMouseTracking(True)
        self.label.setMouseTracking(True)

    def load_image(self, path):
        img = QImage(path)
        if img.isNull():
            return

        img = img.scaled(self.size, self.size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        img.setDevicePixelRatio(self.dpr)
        self.avatar = QPixmap.fromImage(img)
        self.label.setPixmap(
            self.avatar.scaled(self.base_size, self.base_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # GIF 复制到临时文件
        if self.is_gif:
            temp_dir = tempfile.gettempdir()
            self.temp_gif_path = os.path.join(temp_dir, os.path.basename(path))
            shutil.copy(path, self.temp_gif_path)
        else:
            self.temp_gif_path = None

    def enterEvent(self, event):
        if self.is_gif:
            if not self.movie:
                self.movie = QMovie(self.temp_gif_path or self.path)
                self.movie.setScaledSize(self.label.size())
                self.label.setMovie(self.movie)
                self.movie.start()

    def leaveEvent(self, event):
        if self.is_gif and self.movie:
            self.movie.stop()
            self.movie.deleteLater()
            self.movie = None
        self.label.setPixmap(self.avatar.scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        super().leaveEvent(event)

    def stop_movie(self):
        if self.movie:
            self.movie.stop()
            self.label.setMovie(None)
            self.movie.deleteLater()
            self.movie = None

    def setSelected(self, selected: bool):
        self.selected = selected
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            parent_page = self.parent()
            while parent_page and not hasattr(parent_page, "delete_emoji"):
                parent_page = parent_page.parent()

            # 👉 普通单击只做选中逻辑（无论是否编辑模式）
            if hasattr(parent_page, "clear_selection"):
                parent_page.clear_selection()
            self.setSelected(True)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            distance = (event.pos() - self.start_pos).manhattanLength()
            if distance < QApplication.startDragDistance():
                return

            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.path)
            drag.setMimeData(mime)

            pixmap = self.avatar.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

            drag.exec_(Qt.MoveAction)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            parent_page = self.parent()
            # 找到包含 delete_emoji 方法的父页面（EmojiPage）
            while parent_page and not hasattr(parent_page, "delete_emoji"):
                parent_page = parent_page.parent()

            if parent_page and getattr(parent_page, "edit_mode", False):
                # 使用 Fluent 风格对话框重命名

                dialog = RenameEmojiDialog(self.text_label.text(), parent_page)
                if dialog.exec():
                    new_name = dialog.get_text()
                    if new_name:
                        self.text_label.setText(new_name)
                        # 更新数据库
                        eid = None
                        for i in range(parent_page.list_widget.count()):
                            item = parent_page.list_widget.item(i)
                            if parent_page.list_widget.itemWidget(item) == self:
                                eid = item.data(Qt.UserRole)
                                break
                        if eid:
                            parent_page.db.update_emoji_name(eid, new_name)

        super().mouseDoubleClickEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.selected:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            pen = QPen(QColor(0, 120, 215), 1)
            painter.setPen(pen)
            rect = self.rect().adjusted(2, 2, -2, -2)
            painter.drawRoundedRect(rect, 5, 5)

