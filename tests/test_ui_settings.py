"""Settings Page UI Tests using pytest-qt"""
import sys
import os
import tempfile
import json
from pathlib import Path

import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 设置代理环境变量，避免测试时使用代理
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''


@pytest.fixture
def temp_config(qtbot, monkeypatch):
    """创建临时配置文件"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config = {
            "api_key": "",
            "model": "gpt-4o-mini",
            "base_url": "",
            "proxy": "",
            "use_proxy": True,
            "headless": True,
            "cookie": ""
        }
        json.dump(config, f)
        temp_path = f.name

    # 临时修改配置路径
    original_path = Path(__file__).parent.parent / "config.json"
    monkeypatch.setattr('pathlib.Path.exists', lambda self: str(self) == str(original_path) and False)

    yield temp_path

    # 清理
    os.unlink(temp_path)


def test_settings_page_widgets_created(qtbot):
    """测试设置页控件是否正确创建（不检查可见性）"""
    from gui.settings_page import SettingsPage

    window = SettingsPage()
    qtbot.addWidget(window)

    # 验证主要控件存在
    assert window.api_key_input is not None
    assert window.model_input is not None
    assert window.base_url_input is not None
    assert window.test_btn is not None
    assert window.proxy_input is not None
    assert window.use_proxy_cb is not None
    assert window.headless_cb is not None
    assert window.cookie_input is not None

    print("✓ test_settings_page_widgets_created passed - 所有控件已创建")


def test_settings_page_ai_test_button(qtbot):
    """测试 AI 测试按钮状态"""
    from gui.settings_page import SettingsPage

    window = SettingsPage()
    qtbot.addWidget(window)

    # 初始状态应该可用
    assert window.test_btn.isEnabled()
    assert "测试" in window.test_btn.text()

    print("✓ test_settings_page_ai_test_button passed - 测试按钮状态正确")


def test_settings_page_checkbox_toggle(qtbot):
    """测试复选框切换功能"""
    from gui.settings_page import SettingsPage

    window = SettingsPage()
    qtbot.addWidget(window)

    # 切换复选框状态
    window.use_proxy_cb.setChecked(False)
    window.headless_cb.setChecked(False)

    assert window.use_proxy_cb.isChecked() == False
    assert window.headless_cb.isChecked() == False

    # 再次切换回来
    window.use_proxy_cb.setChecked(True)
    window.headless_cb.setChecked(True)

    assert window.use_proxy_cb.isChecked() == True
    assert window.headless_cb.isChecked() == True

    print("✓ test_settings_page_checkbox_toggle passed - 复选框切换正常")


def test_settings_page_input_text(qtbot):
    """测试设置页输入功能"""
    from gui.settings_page import SettingsPage

    window = SettingsPage()
    qtbot.addWidget(window)

    # 测试输入
    window.api_key_input.setText("sk-test-key-123")
    window.model_input.setText("gpt-4o")
    window.base_url_input.setText("https://api.test.com")
    window.proxy_input.setText("http://localhost:8080")

    assert window.api_key_input.text() == "sk-test-key-123"
    assert window.model_input.text() == "gpt-4o"
    assert window.base_url_input.text() == "https://api.test.com"
    assert window.proxy_input.text() == "http://localhost:8080"

    print("✓ test_settings_page_input_text passed - 输入功能正常")


def test_main_window_has_tabs(qtbot):
    """测试主窗口有 Tab 控件"""
    from gui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    # 应该有 Tab 控件
    assert window.tabs is not None
    assert window.tabs.count() >= 3

    print("✓ test_main_window_has_tabs passed - 主窗口有 Tab")


def test_search_page_components(qtbot):
    """测试搜索页组件"""
    from gui.search_page import SearchPage

    window = SearchPage()
    qtbot.addWidget(window)

    # 验证组件存在
    assert window.search_input is not None
    assert window.search_btn is not None
    assert window.results_table is not None

    print("✓ test_search_page_components passed - 搜索页组件正常")


def test_favorites_page_components(qtbot):
    """测试收藏夹页组件"""
    from gui.favorites_page import FavoritesPage

    window = FavoritesPage()
    qtbot.addWidget(window)

    assert window.favorites_table is not None

    print("✓ test_favorites_page_components passed - 收藏夹页组件正常")


def test_ai_test_worker_creation():
    """测试 AI 测试工作线程创建"""
    from gui.settings_page import AITestWorker

    worker = AITestWorker(
        api_key="test-key",
        model="gpt-4o-mini",
        base_url="https://test.com"
    )

    assert worker.api_key == "test-key"
    assert worker.model == "gpt-4o-mini"
    assert worker.base_url == "https://test.com"

    print("✓ test_ai_test_worker_creation passed - AI 测试线程创建正常")


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
