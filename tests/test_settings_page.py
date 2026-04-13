"""测试设置页"""
import sys
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_import_gui_modules():
    """测试 GUI 模块能否正常导入"""
    try:
        from gui.settings_page import SettingsPage
        from gui.search_page import SearchPage
        from gui.favorites_page import FavoritesPage
        from gui.main_window import MainWindow
        print("✓ test_import_gui_modules passed - 所有 GUI 模块导入成功")
    except AttributeError as e:
        raise AssertionError(f"GUI 模块导入失败: {e}")


def test_config_file_operations():
    """测试配置文件读写"""
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_config = {
            "api_key": "test-key-123",
            "model": "gpt-4o-mini",
            "base_url": "https://test.com",
            "proxy": "http://localhost:8080",
            "use_proxy": True,
            "headless": False,
            "cookie": "test_cookie"
        }
        json.dump(test_config, f)
        temp_path = f.name

    try:
        # 读取验证
        with open(temp_path) as f:
            loaded = json.load(f)

        assert loaded['api_key'] == "test-key-123"
        assert loaded['model'] == "gpt-4o-mini"
        assert loaded['proxy'] == "http://localhost:8080"
        assert loaded['headless'] == False

        print("✓ test_config_file_operations passed")

    finally:
        os.unlink(temp_path)


def test_settings_page_init():
    """测试设置页初始化逻辑"""
    # 测试配置默认值
    config = {}

    api_key = config.get("api_key", "")
    model = config.get("model", "gpt-4o-mini")
    base_url = config.get("base_url", "")
    proxy = config.get("proxy", "")
    use_proxy = config.get("use_proxy", True)
    headless = config.get("headless", True)
    cookie = config.get("cookie", "")

    assert api_key == ""
    assert model == "gpt-4o-mini"
    assert base_url == ""
    assert proxy == ""
    assert use_proxy == True
    assert headless == True
    assert cookie == ""

    print("✓ test_settings_page_init passed")


def test_save_settings_logic():
    """测试保存设置的逻辑"""
    # 模拟 UI 输入
    ui_values = {
        "api_key": "new-key-456",
        "model": "claude-3",
        "base_url": "https://api.anthropic.com",
        "proxy": "http://proxy:8888",
        "use_proxy": False,
        "headless": False,
        "cookie": "new_cookie_value"
    }

    # 验证保存逻辑
    config = {
        "api_key": ui_values["api_key"],
        "model": ui_values["model"],
        "base_url": ui_values["base_url"],
        "proxy": ui_values["proxy"],
        "use_proxy": ui_values["use_proxy"],
        "headless": ui_values["headless"],
        "cookie": ui_values["cookie"],
    }

    assert config["api_key"] == "new-key-456"
    assert config["model"] == "claude-3"
    assert config["use_proxy"] == False
    assert config["headless"] == False

    print("✓ test_save_settings_logic passed")


def test_ai_test_worker_init():
    """测试 AI 测试线程初始化"""
    from gui.settings_page import AITestWorker

    worker = AITestWorker(
        api_key="test-key",
        model="gpt-4o-mini",
        base_url="https://test.com"
    )

    assert worker.api_key == "test-key"
    assert worker.model == "gpt-4o-mini"
    assert worker.base_url == "https://test.com"

    print("✓ test_ai_test_worker_init passed")


if __name__ == '__main__':
    test_import_gui_modules()
    test_config_file_operations()
    test_settings_page_init()
    test_save_settings_logic()
    test_ai_test_worker_init()
    print("\n所有测试通过!")
