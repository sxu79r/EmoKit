import sys, os, shutil, sqlite3
from functools import partial
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QListWidget, QListWidgetItem, QInputDialog,
                             QFileDialog, QMenu, QStackedWidget)
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QImage, QBrush, QColor, QFont
from PyQt5.QtCore import Qt, QRect, QSize
from qfluentwidgets import NavigationInterface, NavigationItemPosition, PushButton, NavigationWidget, FluentIcon as FIF
from qframelesswindow import FramelessWindow
from gui.MainWindows import EmojiManager
from core.LoadSettings import cfg

def save_config_on_exit():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, 'config/config.json')
    cfg.save(path)
    print(1)

def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)

    window = EmojiManager()
    window.show()

    app.aboutToQuit.connect(save_config_on_exit)

    sys.exit(app.exec_())




if __name__ == '__main__':
    main()