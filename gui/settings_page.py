"""设置页 - LLM API Key 和代理配置"""
import os
import json
import asyncio
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QGroupBox,
    QCheckBox, QMessageBox, QTextEdit, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal


class AITestWorker(QThread):
    """AI 测试工作线程"""
    finished = pyqtSignal(bool, str)

    def __init__(self, api_key, model, base_url):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def run(self):
        try:
            # 清除代理设置
            for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
                os.environ.pop(var, None)

            if self.base_url:
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            else:
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key)

            response = client.chat.completions.create(
                model=self.model or "gpt-4o-mini",
                messages=[{"role": "user", "content": "Hi, please reply 'OK' if you receive this message."}],
                max_tokens=10
            )

            reply = response.choices[0].message.content
            if "ok" in reply.lower():
                self.finished.emit(True, "AI 连接成功！")
            else:
                self.finished.emit(False, f"AI 返回异常: {reply}")

        except Exception as e:
            self.finished.emit(False, f"AI 连接失败: {str(e)}")


class SettingsPage(QWidget):
    """设置页面"""

    def __init__(self):
        super().__init__()
        self.config_path = Path(__file__).parent.parent / "config.json"
        self.load_config()
        self.test_worker = None

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # LLM 设置
        llm_group = QGroupBox("AI 设置")
        llm_layout = QFormLayout()
        llm_layout.setHorizontalSpacing(10)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        self.api_key_input.setText(self.config.get("api_key", ""))
        llm_layout.addRow("API Key:", self.api_key_input)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("gpt-4o-mini / claude-3-haiku")
        self.model_input.setText(self.config.get("model", "gpt-4o-mini"))
        llm_layout.addRow("模型:", self.model_input)

        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("https://api.openai.com/v1 (留空使用默认)")
        self.base_url_input.setText(self.config.get("base_url", ""))
        llm_layout.addRow("API Base URL:", self.base_url_input)

        # 测试按钮
        test_layout = QHBoxLayout()
        self.test_btn = QPushButton("🧪 测试连接")
        self.test_btn.clicked.connect(self.test_ai_connection)
        self.test_btn.setMaximumWidth(120)
        test_layout.addWidget(self.test_btn)
        test_layout.addWidget(QLabel(""))

        self.test_result_label = QLabel("")
        test_layout.addWidget(self.test_result_label, 1)
        llm_layout.addRow("", test_layout)

        llm_group.setLayout(llm_layout)
        layout.addWidget(llm_group)

        # 代理设置
        proxy_group = QGroupBox("代理设置")
        proxy_layout = QFormLayout()
        proxy_layout.setHorizontalSpacing(10)

        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("http://127.0.0.1:7890")
        self.proxy_input.setText(self.config.get("proxy", ""))
        proxy_layout.addRow("HTTP Proxy:", self.proxy_input)

        self.use_proxy_cb = QCheckBox("启用代理")
        self.use_proxy_cb.setChecked(self.config.get("use_proxy", True))
        proxy_layout.addRow("", self.use_proxy_cb)

        proxy_group.setLayout(proxy_layout)
        layout.addWidget(proxy_group)

        # 浏览器设置
        browser_group = QGroupBox("浏览器设置")
        browser_layout = QFormLayout()
        browser_layout.setHorizontalSpacing(10)

        self.headless_cb = QCheckBox("无头模式 (不显示浏览器)")
        self.headless_cb.setChecked(self.config.get("headless", True))
        browser_layout.addRow("", self.headless_cb)

        browser_group.setLayout(browser_layout)
        layout.addWidget(browser_group)

        # Cookie 设置
        cookie_group = QGroupBox("小红书 Cookie")
        cookie_layout = QVBoxLayout()

        cookie_info = QLabel(
            "Cookie 用于登录小红书。<br>"
            "获取方法：浏览器登录小红书 → F12 → Application → Cookies → 复制其中的 cookie 值"
        )
        cookie_info.setStyleSheet("color: gray;")
        cookie_layout.addWidget(cookie_info)

        self.cookie_input = QTextEdit()
        self.cookie_input.setMaximumHeight(80)
        self.cookie_input.setPlaceholderText("请粘贴小红书 Cookie...")
        self.cookie_input.setPlainText(self.config.get("cookie", ""))
        cookie_layout.addWidget(self.cookie_input)

        cookie_group.setLayout(cookie_layout)
        layout.addWidget(cookie_group)

        # 保存按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

        self.setLayout(layout)

    def load_config(self):
        """加载配置"""
        self.config = {}
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            except:
                self.config = {}

    def save_settings(self):
        """保存设置"""
        self.config = {
            "api_key": self.api_key_input.text().strip(),
            "model": self.model_input.text().strip(),
            "base_url": self.base_url_input.text().strip(),
            "proxy": self.proxy_input.text().strip(),
            "use_proxy": self.use_proxy_cb.isChecked(),
            "headless": self.headless_cb.isChecked(),
            "cookie": self.cookie_input.toPlainText().strip(),
        }

        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

        QMessageBox.information(self, "保存成功", "设置已保存！")

    def test_ai_connection(self):
        """测试 AI 连接"""
        api_key = self.api_key_input.text().strip()
        model = self.model_input.text().strip()
        base_url = self.base_url_input.text().strip()

        if not api_key:
            QMessageBox.warning(self, "提示", "请先输入 API Key")
            return

        self.test_btn.setEnabled(False)
        self.test_btn.setText("测试中...")
        self.test_result_label.setText("")

        self.test_worker = AITestWorker(api_key, model, base_url)
        self.test_worker.finished.connect(self.on_test_finished)
        self.test_worker.start()

    def on_test_finished(self, success, message):
        """AI 测试完成"""
        self.test_btn.setEnabled(True)
        self.test_btn.setText("🧪 测试连接")

        if success:
            self.test_result_label.setText(f"<span style='color: green;'>✓ {message}</span>")
        else:
            self.test_result_label.setText(f"<span style='color: red;'>✗ {message}</span>")
