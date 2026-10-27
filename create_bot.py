from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from decouple import config
from aiogram.fsm.storage.memory import MemoryStorage

# переменные для работы
APP_VERSION = "1.1.1"
ADMIN_ID = int(config('ADMIN_ID'))
BOT_TOKEN = config("BOT_TOKEN")
HOST = config("HOST", default="127.0.0.1")
PORT = int(config("PORT", default=8041))
WEBHOOK_PATH = config("WEBHOOK_PATH", default="/telegram/webhook")
WEBHOOK_SECRET = config("WEBHOOK_SECRET")
BASE_URL = config("BASE_URL").rstrip("/")

kb_list = [{'label': 'Легкий путь в Python', 'url': 'https://t.me/PythonPathMaster'}]

# инициализируем бота и диспетчера для работы с ними
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
