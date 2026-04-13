"""搜索页 - 关键词搜索和结果展示"""
import os
import sys
import asyncio
import json
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QProgressBar,
    QGroupBox, QMessageBox, QSplitter, QTextEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont


class SearchWorker(QThread):
    """搜索工作线程"""
    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str, int)
    result_ready = pyqtSignal(list)

    def __init__(self, keyword, config):
        super().__init__()
        self.keyword = keyword
        self.config = config

    def run(self):
        try:
            self.progress.emit("正在初始化...", 5)

            # 设置代理环境变量
            if self.config.get('use_proxy') and self.config.get('proxy'):
                os.environ['HTTP_PROXY'] = self.config['proxy']
                os.environ['HTTPS_PROXY'] = self.config['proxy']

            # 设置 Cookie
            cookie = self.config.get('cookie', '')
            if cookie:
                os.environ['XHS_COOKIE'] = cookie

            # 动态导入
            project_root = Path(__file__).parent.parent
            sys.path.insert(0, str(project_root))

            from src.storage import Storage
            from src.ai_analyzer import AIAnalyzer
            from src.config import HEADLESS

            self.progress.emit("正在搜索笔记...", 20)

            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                async def crawl_task():
                    storage = Storage()
                    from src.crawler import XiaohongshuCrawler
                    crawler = XiaohongshuCrawler(storage)

                    # 设置 headless 模式
                    original_headless = HEADLESS
                    if self.config.get('headless') is not None:
                        os.environ['HEADLESS'] = 'true' if self.config['headless'] else 'false'
                        # 临时修改 config
                        import src.config as cfg
                        cfg.HEADLESS = self.config.get('headless', True)

                    await crawler.start()

                    try:
                        # 爬取关键词
                        notes = await crawler.crawl_keyword(self.keyword)
                        self.progress.emit(f"找到 {len(notes)} 个笔记", 50)

                        if not notes:
                            self.progress.emit("未找到笔记", 100)
                            self.result_ready.emit([])
                            return

                        # 获取所有评论
                        all_comments = []
                        for i, note in enumerate(notes):
                            comments = storage.get_comments_for_note(note['note_id'])
                            all_comments.extend(comments)
                            self.progress.emit(
                                f"处理笔记 {i+1}/{len(notes)}...",
                                50 + (i * 30 // len(notes))
                            )

                        self.progress.emit(f"获取到 {len(all_comments)} 条评论", 70)

                        if all_comments:
                            # AI 清洗
                            analyzer = AIAnalyzer(storage)
                            cleaned = analyzer.clean_comments_batch(all_comments)
                            self.progress.emit(f"AI 清洗完成，获取 {len(cleaned)} 条创意", 90)
                            self.result_ready.emit(cleaned)
                        else:
                            self.progress.emit("没有评论数据", 100)
                            self.result_ready.emit([])

                    finally:
                        await crawler.close()
                        # 恢复原始设置
                        import src.config as cfg
                        cfg.HEADLESS = original_headless

                loop.run_until_complete(crawl_task())

            finally:
                loop.close()

            self.progress.emit("搜索完成", 100)
            self.finished.emit(True, "搜索完成")

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.finished.emit(False, str(e))


class SearchPage(QWidget):
    """搜索页面"""

    search_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.current_results = []
        self.project_root = Path(__file__).parent.parent
        self.config_path = self.project_root / "config.json"

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 搜索框
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索小红书创意...")
        self.search_input.returnPressed.connect(self.start_search)

        self.search_btn = QPushButton("🔍 搜索")
        self.search_btn.clicked.connect(self.start_search)
        search_layout.addWidget(QLabel("关键词:"))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)

        main_layout.addLayout(search_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel("")
        main_layout.addWidget(self.status_label)

        # 结果区域（使用 splitter）
        splitter = QSplitter(Qt.Vertical)

        # 表格
        results_group = QGroupBox("搜索结果")
        results_layout = QVBoxLayout()

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "创意内容", "用户", "点赞", "可行性", "笔记来源", "操作"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(1, 80)
        self.results_table.horizontalHeader().setSectionResizeMode(2, 50)
        self.results_table.horizontalHeader().setSectionResizeMode(3, 50)
        self.results_table.horizontalHeader().setSectionResizeMode(4, 120)
        self.results_table.horizontalHeader().setSectionResizeMode(5, 60)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setMinimumHeight(200)

        results_layout.addWidget(self.results_table)
        results_group.setLayout(results_layout)
        splitter.addWidget(results_group)

        main_layout.addWidget(splitter)

        self.setLayout(main_layout)

    def load_config(self):
        """加载配置"""
        config = {}
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
            except:
                pass
        return config

    def start_search(self):
        """开始搜索"""
        keyword = self.search_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入关键词")
            return

        # 检查配置
        config = self.load_config()
        if not config.get('cookie'):
            QMessageBox.warning(
                self, "配置不完整",
                "请先在设置页面填写小红书 Cookie"
            )
            return

        # 禁用搜索按钮
        self.search_btn.setEnabled(False)
        self.search_input.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在搜索...")
        self.results_table.setRowCount(0)

        # 启动搜索线程
        self.worker = SearchWorker(keyword, config)
        self.worker.progress.connect(self.on_progress)
        self.worker.result_ready.connect(self.on_results_ready)
        self.worker.finished.connect(self.on_search_finished)
        self.worker.start()

    def on_progress(self, message, percentage):
        """更新进度"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)

    def on_results_ready(self, results):
        """显示搜索结果"""
        self.current_results = results
        self.results_table.setRowCount(len(results))

        for i, item in enumerate(results):
            # 创意内容
            content = item.get('cleaned_view', item.get('original_content', ''))
            self.results_table.setItem(i, 0, QTableWidgetItem(content))
            # 用户
            self.results_table.setItem(i, 1, QTableWidgetItem(item.get('user', '')))
            # 点赞
            self.results_table.setItem(i, 2, QTableWidgetItem(str(item.get('like_count', 0))))
            # 可行性
            score = item.get('feasibility_score', item.get('score', ''))
            self.results_table.setItem(i, 3, QTableWidgetItem(str(score)))
            # 笔记来源
            note_title = item.get('note_title', '')[:20]
            self.results_table.setItem(i, 4, QTableWidgetItem(note_title))

            # 收藏按钮
            fav_btn = QPushButton("⭐")
            fav_btn.clicked.connect(lambda checked, r=item: self.add_to_favorites(r))
            self.results_table.setCellWidget(i, 5, fav_btn)

        self.status_label.setText(f"找到 {len(results)} 条创意")

    def on_search_finished(self, success, message):
        """搜索完成"""
        self.search_btn.setEnabled(True)
        self.search_input.setEnabled(True)
        self.progress_bar.setVisible(False)

        if not success:
            self.status_label.setText(f"搜索失败: {message}")
            QMessageBox.critical(self, "错误", f"搜索失败:\n{message}")

    def add_to_favorites(self, item):
        """添加到收藏夹"""
        # 延迟导入避免循环依赖
        from gui.favorites_page import FavoritesPage
        favorites_page = self.window().findChild(FavoritesPage)
        if favorites_page:
            favorites_page.add_favorite(item)
        else:
            QMessageBox.information(self, "收藏", f"已收藏: {item.get('cleaned_view', '')[:30]}...")
