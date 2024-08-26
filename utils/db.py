import aiosqlite


async def initialize_database():
    # Подключаемся к базе данных (если база данных не существует, она будет создана)
    async with aiosqlite.connect("bot.db") as db:
        # Создаем таблицу users, если она не существует
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                bot_open BOOLEAN DEFAULT FALSE
            )
        """)
        # Сохраняем изменения
        await db.commit()


async def add_user(telegram_id: int, username: str, first_name: str):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""
            INSERT INTO users (telegram_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO NOTHING
        """, (telegram_id, username, first_name))
        await db.commit()


# Функция для получения всех пользователей в виде списка словарей
async def get_all_users():
    async with aiosqlite.connect("bot.db") as db:
        cursor = await db.execute("SELECT * FROM users")
        rows = await cursor.fetchall()

        # Преобразуем результаты в список словарей
        users = [
            {
                "telegram_id": row[0],
                "username": row[1],
                "first_name": row[2],
                "bot_open": bool(row[3])
            }
            for row in rows
        ]
        return users


# Функция для обновления статуса bot_open по telegram_id
async def update_bot_open_status(telegram_id: int, bot_open: bool):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""
            UPDATE users
            SET bot_open = ?
            WHERE telegram_id = ?
        """, (bot_open, telegram_id))
        await db.commit()


# Функция для получения данных о пользователе по telegram_id в виде словаря
async def get_user_by_id(telegram_id: int):
    async with aiosqlite.connect("bot.db") as db:
        cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cursor.fetchone()

        if row is None:
            return None

        # Преобразуем результат в словарь
        user = {
            "telegram_id": row[0],
            "username": row[1],
            "first_name": row[2],
            "bot_open": bool(row[3])
        }
        return user
