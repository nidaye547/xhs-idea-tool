"""主窗口 - 包含搜索、收藏夹、设置三个页面"""
import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QStatusBar, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon

from .search_page import SearchPage
from .favorites_page import FavoritesPage
from .settings_page import SettingsPage


class CrawlerWorker(QThread):
    """爬虫工作线程，避免阻塞 UI"""
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)

    def __init__(self, crawler_func, keyword):
        super().__init__()
        self.crawler_func = crawler_func
        self.keyword = keyword

    def run(self):
        try:
            self.progress.emit(f"正在搜索: {self.keyword}")
            # 这里会调用爬虫逻辑
            # 暂时先模拟
            import time
            time.sleep(2)
            self.finished.emit(True, "搜索完成")
        except Exception as e:
            self.finished.emit(False, str(e))


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("小红书创意发现工具")
        self.setMinimumSize(1000, 700)

        # 创建 Tab 页面
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.West)  # 左侧标签
        self.tabs.setTabWhatsThis(0, "搜索")
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                min-width: 120px;
                padding: 10px;
                font-size: 14px;
            }
        """)

        # 搜索页
        self.search_page = SearchPage()
        self.search_page.search_requested.connect(self.on_search_requested)
        self.tabs.addTab(self.search_page, "🔍 搜索")

        # 收藏夹页
        self.favorites_page = FavoritesPage()
        self.tabs.addTab(self.favorites_page, "⭐ 收藏夹")
        self.favorites_page.add_favorite = self.favorites_page.add_favorite  # 暴露方法

        # 设置页
        self.settings_page = SettingsPage()
        self.tabs.addTab(self.settings_page, "⚙️ 设置")

        self.setCentralWidget(self.tabs)

        # 状态栏
        self.statusBar().showMessage("就绪")

    def on_search_requested(self, keyword):
        """处理搜索请求"""
        self.statusBar().showMessage(f"正在搜索: {keyword}...")
        self.tabs.setCurrentIndex(0)  # 切回搜索页

    def closeEvent(self, event):
        """关闭时确认"""
        reply = QMessageBox.question(
            self, '确认退出',
            '确定要退出吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
