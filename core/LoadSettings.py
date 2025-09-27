import os
from qfluentwidgets import (
    qconfig, QConfig, ConfigItem, ColorConfigItem, OptionsConfigItem, OptionsValidator, RangeConfigItem, RangeValidator, FolderValidator, ColorValidator, BoolValidator
    )


class Config(QConfig):
    # ================================
    # 软件相关
    # ================================
    Vision = ConfigItem("Software","Vision",default="v0.5")
    # ================================
    # 路径设置
    # ================================
    EmojiSaved_Path = ConfigItem("Emoji", "Save_Path", "./emojis")
    EmojiDB_Path = ConfigItem("Emoji", "DB_Path", "./emojis.db")
    # ================================
    # 窗口设置
    # ================================
    Tray_State=ConfigItem("Windows","Tray",True,BoolValidator())
    Automatic_Startup = ConfigItem("Windows", "Automatic_Startup", True, BoolValidator())
    ThemeColor = ColorConfigItem("Windows",",ThemeColor","#004e27")
    # ================================
    # 快捷键设置
    # ================================
    Hotkey = ConfigItem("Windows", "Hotkey", True, BoolValidator())

# ================================
# 加载配置
# ================================

script_dir = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(script_dir, '../config/config.json')
cfg = Config()
qconfig.load(path, cfg)
