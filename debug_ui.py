"""UI 布局调试脚本 - 输出 UI 结构供分析"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from gui.main_window import MainWindow


def dump_widget_tree(widget, indent=0):
    """输出控件树结构"""
    prefix = "  " * indent
    widget_type = widget.__class__.__name__

    # 获取控件的关键信息
    info = []
    if hasattr(widget, 'text') and callable(widget.text):
        text = widget.text()
        if text:
            info.append(f'text="{text[:30]}"')

    if hasattr(widget, 'placeholderText'):
        pt = widget.placeholderText()
        if pt:
            info.append(f'placeholder="{pt[:30]}"')

    if hasattr(widget, 'windowTitle'):
        wt = widget.windowTitle()
        if wt:
            info.append(f'title="{wt}"')

    info_str = f" ({', '.join(info)})" if info else ""

    print(f"{prefix}{widget_type}{info_str}")

    # 递归处理子控件
    if hasattr(widget, 'children'):
        for child in widget.children():
            # 跳过内部控件
            if child.__class__.__name__ in ('QWindow', 'QWidget', 'QAction'):
                dump_widget_tree(child, indent + 1)


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 创建主窗口
    window = MainWindow()

    print("=" * 60)
    print("主窗口 UI 结构")
    print("=" * 60)
    dump_widget_tree(window)

    print("\n" + "=" * 60)
    print("搜索页 UI 结构")
    print("=" * 60)
    dump_widget_tree(window.search_page)

    print("\n" + "=" * 60)
    print("收藏夹页 UI 结构")
    print("=" * 60)
    dump_widget_tree(window.favorites_page)

    print("\n" + "=" * 60)
    print("设置页 UI 结构")
    print("=" * 60)
    dump_widget_tree(window.settings_page)

    print("\n" + "=" * 60)
    print("样式表信息")
    print("=" * 60)
    print(f"主窗口样式长度: {len(window.styleSheet())} 字符")
    print(f"搜索页样式长度: {len(window.search_page.styleSheet())} 字符")
    print(f"收藏夹页样式长度: {len(window.favorites_page.styleSheet())} 字符")
    print(f"设置页样式长度: {len(window.settings_page.styleSheet())} 字符")


if __name__ == '__main__':
    main()
