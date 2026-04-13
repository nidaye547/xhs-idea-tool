import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent.parent
KEYWORDS_FILE = os.getenv("KEYWORDS_FILE", str(BASE_DIR / "keywords.txt"))
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "xiaohongshu.db"))
OUTPUT_DIR = BASE_DIR / "output"

# Playwright settings
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
COMMENT_SCROLL_PAUSE = float(os.getenv("COMMENT_SCROLL_PAUSE", "1.5"))  # 滚动后等待时间
MAX_NOTES_PER_KEYWORD = int(os.getenv("MAX_NOTES_PER_KEYWORD", "10"))

# Rate limiting - request delays to avoid triggering anti-bot
MAX_CONCURRENT_PAGES = int(os.getenv("MAX_CONCURRENT_PAGES", "5"))  # 每批处理5个笔记
BATCH_DELAY = int(os.getenv("BATCH_DELAY", "30"))  # 批次间延迟30秒
NOTE_DELAY_MIN = int(os.getenv("NOTE_DELAY_MIN", "2"))  # 笔记间最小延迟(秒)
NOTE_DELAY_MAX = int(os.getenv("NOTE_DELAY_MAX", "5"))  # 笔记间最大延迟(秒)
SEARCH_DELAY_MIN = int(os.getenv("SEARCH_DELAY_MIN", "3"))  # 搜索间最小延迟(秒)
SEARCH_DELAY_MAX = int(os.getenv("SEARCH_DELAY_MAX", "8"))  # 搜索间最大延迟(秒)

# Scheduler settings
CRAWL_HOUR = int(os.getenv("CRAWL_HOUR", "2"))
CRAWL_MINUTE = int(os.getenv("CRAWL_MINUTE", "0"))
CRAWL_INTERVAL_HOURS = int(os.getenv("CRAWL_INTERVAL_HOURS", "6"))

# AI settings
AI_BATCH_SIZE = int(os.getenv("AI_BATCH_SIZE", "30"))
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")  # "openai" or "anthropic"
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", None)  # Custom endpoint for MiniMax etc.

# Xiaohongshu URLs
BASE_URL = "https://www.xiaohongshu.com"
SEARCH_URL = f"{BASE_URL}/search_result"

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
