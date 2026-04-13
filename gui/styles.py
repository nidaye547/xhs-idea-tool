"""全局样式表 - 统一应用外观"""
from PyQt5.QtWidgets import QWidget

# 主色调
PRIMARY_COLOR = "#4A90D9"
PRIMARY_HOVER = "#3A7BC8"
SUCCESS_COLOR = "#52c41a"
DANGER_COLOR = "#ff4d4f"
WARNING_COLOR = "#faad14"

# 字体
FONT_FAMILY = "Microsoft YaHei, PingFang SC, Helvetica Neue, Arial, sans-serif"

# 基础样式表
BASE_STYLESHEET = f"""
    QWidget {{
        font-family: {FONT_FAMILY};
        font-size: 13px;
    }}

    QLabel {{
        color: #333;
    }}
"""

# 主窗口样式
MAIN_WINDOW_STYLESHEET = f"""
    QMainWindow {{
        background-color: #f5f5f5;
    }}

    QTabWidget::pane {{
        border: none;
        background-color: white;
    }}

    QTabBar {{
        background-color: #f0f0f0;
    }}

    QTabBar::tab {{
        background-color: #e0e0e0;
        color: #555;
        padding: 8px 10px;
        margin: 2px 0;
        border: none;
        border-radius: 0;
        font-size: 12px;
        font-weight: 500;
        min-width: 40px;
    }}

    QTabBar::tab:selected {{
        background-color: white;
        color: #333;
        font-weight: bold;
        border-left: 3px solid {PRIMARY_COLOR};
    }}

    QTabBar::tab:hover:!selected {{
        background-color: #d8d8d8;
    }}
"""

# 按钮样式
BUTTON_STYLESHEET = f"""
    QPushButton {{
        background-color: {PRIMARY_COLOR};
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 20px;
        font-size: 14px;
        font-weight: 500;
    }}

    QPushButton:hover {{
        background-color: {PRIMARY_HOVER};
    }}

    QPushButton:pressed {{
        background-color: #2d6aa8;
        padding-top: 11px;
        padding-bottom: 9px;
    }}

    QPushButton:disabled {{
        background-color: #ccc;
        color: #888;
    }}
"""

# 次要按钮样式
SECONDARY_BUTTON_STYLESHEET = """
    QPushButton {
        background-color: #f5f5f5;
        color: #333;
        border: 1px solid #ddd;
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 13px;
    }

    QPushButton:hover {
        background-color: #e8e8e8;
        border-color: #ccc;
    }

    QPushButton:pressed {
        background-color: #ddd;
    }
"""

# 危险按钮样式
DANGER_BUTTON_STYLESHEET = f"""
    QPushButton {{
        background-color: {DANGER_COLOR};
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 13px;
    }}

    QPushButton:hover {{
        background-color: #e63c3c;
    }}
"""

# 输入框样式
LINE_EDIT_STYLESHEET = """
    QLineEdit {
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 6px 10px;
        background-color: white;
        font-size: 13px;
        color: #333;
        min-height: 28px;
    }

    QLineEdit:focus {
        border-color: #4A90D9;
        background-color: #f8f9fa;
    }

    QLineEdit:hover {
        border-color: #bbb;
    }

    QLineEdit:placeholder {
        color: #aaa;
    }
"""

# 文本编辑框样式
TEXT_EDIT_STYLESHEET = """
    QTextEdit {
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 8px;
        background-color: white;
        font-size: 13px;
        color: #333;
    }

    QTextEdit:focus {
        border-color: #4A90D9;
        background-color: #f8f9fa;
    }

    QTextEdit:hover {
        border-color: #bbb;
    }
"""

# 表格样式
TABLE_STYLESHEET = """
    QTableWidget {
        border: none;
        background-color: white;
        gridline-color: #f0f0f0;
        selection-background-color: #e6f0ff;
        font-size: 13px;
    }

    QTableWidget::item {
        padding: 4px;
        border: none;
        border-bottom: 1px solid #f0f0f0;
        color: #333;
    }

    QTableWidget::item:selected {
        background-color: #e6f0ff;
        color: #333;
    }

    QHeaderView::section {
        background-color: #f8f9fa;
        color: #333;
        font-weight: bold;
        padding: 8px;
        border: none;
        border-bottom: 2px solid #4A90D9;
    }

    QHeaderView {
        border: none;
    }

    QTableWidget::item:alternate {
        background-color: #f5f7fb;
    }

    QTableCornerButton::section {
        background-color: #f8f9fa;
        border: none;
    }
"""

# 分组框样式
GROUP_BOX_STYLESHEET = """
    QGroupBox {
        font-weight: bold;
        font-size: 14px;
        color: #333;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        margin-top: 10px;
        padding: 10px;
        background-color: white;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
        color: #4A90D9;
    }
"""

# 进度条样式
PROGRESS_BAR_STYLESHEET = f"""
    QProgressBar {{
        border: none;
        border-radius: 6px;
        background-color: #e8e8e8;
        text-align: center;
        color: white;
        font-weight: 500;
    }}

    QProgressBar::chunk {{
        background-color: {PRIMARY_COLOR};
        border-radius: 6px;
    }}
"""

# 复选框样式
CHECKBOX_STYLESHEET = """
    QCheckBox {
        spacing: 10px;
        font-size: 14px;
        color: #333;
    }

    QCheckBox::indicator {
        width: 20px;
        height: 20px;
        border-radius: 4px;
        border: 2px solid #ccc;
        background-color: white;
    }

    QCheckBox::indicator:checked {
        background-color: #4A90D9;
        border-color: #4A90D9;
    }

    QCheckBox::indicator:hover {
        border-color: #4A90D9;
    }

    QCheckBox:hover {
        color: #4A90D9;
    }
"""

# 状态栏样式
STATUS_BAR_STYLESHEET = """
    QStatusBar {
        background-color: #f8f9fa;
        color: #666;
        border-top: 1px solid #e0e0e0;
        padding: 6px;
        font-size: 12px;
    }
"""

# 灰色文字样式
GRAY_TEXT_STYLESHEET = """
    QLabel {
        color: gray;
        font-size: 13px;
    }
"""

# 标签样式
LABEL_STYLESHEET = """
    QLabel {
        color: #333;
        font-size: 13px;
    }
"""

# 标题标签样式
TITLE_LABEL_STYLESHEET = """
    QLabel {
        color: #333;
        font-size: 16px;
        font-weight: bold;
    }
"""

# 空状态提示样式
EMPTY_LABEL_STYLESHEET = """
    QLabel {
        color: #999;
        font-size: 14px;
        padding: 50px;
    }
"""

# 状态标签样式
STATUS_LABEL_STYLESHEET = """
    QLabel {
        color: #666;
        font-size: 13px;
        padding: 4px 0;
    }
"""

# 设置页特定样式
SETTINGS_PAGE_STYLESHEET = f"""
    QGroupBox {{
        font-weight: bold;
        font-size: 13px;
        color: #333333;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        margin-top: 10px;
        padding: 10px 10px 8px 10px;
        background-color: white;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
        background-color: white;
        color: #4A90D9;
    }}

    QFormLayout {{
        label-min-width: 100px;
    }}

    QFormLayout > QLabel {{
        color: #333333;
        font-size: 13px;
        min-width: 100px;
        padding-right: 10px;
    }}
"""


def apply_styles(widget):
    """递归应用样式到所有子控件"""
    widget.setStyleSheet(BASE_STYLESHEET)
    for child in widget.findChildren(QWidget):
        if not child.styleSheet():
            child.setStyleSheet(BASE_STYLESHEET)