"""收藏夹页 - 显示和管理收藏的创意"""
import json
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QGroupBox, QLabel, QMessageBox
)
from PyQt5.QtCore import Qt


class FavoritesPage(QWidget):
    """收藏夹页面"""

    def __init__(self):
        super().__init__()
        self.favorites_path = Path(__file__).parent.parent / "favorites.json"
        self.load_favorites()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 标题栏
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("<h2>⭐ 我的收藏夹</h2>"))
        title_layout.addStretch()

        # 操作按钮
        export_btn = QPushButton("📤 导出")
        export_btn.clicked.connect(self.export_favorites)
        title_layout.addWidget(export_btn)

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.load_favorites)
        title_layout.addWidget(refresh_btn)

        main_layout.addLayout(title_layout)

        # 收藏列表
        results_group = QGroupBox(f"已收藏 ({len(self.favorites)}) 个创意")
        results_layout = QVBoxLayout()

        self.favorites_table = QTableWidget()
        self.favorites_table.setColumnCount(6)
        self.favorites_table.setHorizontalHeaderLabels([
            "创意内容", "用户", "点赞", "可行性", "来源笔记", "操作"
        ])
        self.favorites_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.favorites_table.horizontalHeader().setSectionResizeMode(1, 80)
        self.favorites_table.horizontalHeader().setSectionResizeMode(2, 50)
        self.favorites_table.horizontalHeader().setSectionResizeMode(3, 50)
        self.favorites_table.horizontalHeader().setSectionResizeMode(4, 150)
        self.favorites_table.horizontalHeader().setSectionResizeMode(5, 60)
        self.favorites_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.favorites_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.favorites_table.setAlternatingRowColors(True)

        results_layout.addWidget(self.favorites_table)
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)

        # 空状态提示
        self.empty_label = QLabel("收藏夹是空的，去搜索页面添加收藏吧！")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: gray; font-size: 14px; padding: 50px;")
        self.empty_label.setVisible(len(self.favorites) == 0)
        main_layout.addWidget(self.empty_label)

        self.setLayout(main_layout)
        self.populate_table()

    def load_favorites(self):
        """加载收藏"""
        self.favorites = []
        if self.favorites_path.exists():
            try:
                with open(self.favorites_path, 'r', encoding='utf-8') as f:
                    self.favorites = json.load(f)
            except:
                self.favorites = []

    def save_favorites(self):
        """保存收藏"""
        with open(self.favorites_path, 'w', encoding='utf-8') as f:
            json.dump(self.favorites, f, ensure_ascii=False, indent=2)

    def add_favorite(self, item):
        """添加收藏"""
        # 检查是否已收藏（基于 content 哈希）
        content_hash = hash(item.get('cleaned_view', ''))
        for fav in self.favorites:
            if hash(fav.get('cleaned_view', '')) == content_hash:
                QMessageBox.information(self, "提示", "该项目已收藏！")
                return

        self.favorites.append(item)
        self.save_favorites()
        self.populate_table()
        QMessageBox.information(self, "成功", "已添加到收藏夹！")

    def remove_favorite(self, index):
        """移除收藏"""
        if 0 <= index < len(self.favorites):
            del self.favorites[index]
            self.save_favorites()
            self.populate_table()

    def populate_table(self):
        """填充表格"""
        self.favorites_table.setRowCount(len(self.favorites))

        for i, item in enumerate(self.favorites):
            self.favorites_table.setItem(i, 0, QTableWidgetItem(item.get('cleaned_view', '')))
            self.favorites_table.setItem(i, 1, QTableWidgetItem(item.get('user', '')))
            self.favorites_table.setItem(i, 2, QTableWidgetItem(str(item.get('like_count', 0))))
            self.favorites_table.setItem(i, 3, QTableWidgetItem(str(item.get('feasibility_score', ''))))
            self.favorites_table.setItem(i, 4, QTableWidgetItem(item.get('note_title', '')[:20]))

            # 删除按钮
            from PyQt5.QtWidgets import QPushButton
            del_btn = QPushButton("🗑️")
            del_btn.clicked.connect(lambda checked, idx=i: self.remove_favorite(idx))
            self.favorites_table.setCellWidget(i, 5, del_btn)

        self.empty_label.setVisible(len(self.favorites) == 0)

    def export_favorites(self):
        """导出收藏到 CSV"""
        if not self.favorites:
            QMessageBox.information(self, "提示", "收藏夹是空的！")
            return

        from PyQt5.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出收藏", "favorites.csv", "CSV Files (*.csv)"
        )

        if filepath:
            import csv
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['创意内容', '用户', '点赞', '可行性', '来源笔记'])
                for item in self.favorites:
                    writer.writerow([
                        item.get('cleaned_view', ''),
                        item.get('user', ''),
                        item.get('like_count', 0),
                        item.get('feasibility_score', ''),
                        item.get('note_title', '')
                    ])
            QMessageBox.information(self, "成功", f"已导出到 {filepath}")
