"""Exercise real dispatcher routing without contacting Telegram or the production DB."""

import importlib
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ.update({
    "BOT_TOKEN": "123456:TEST_TOKEN_FOR_OFFLINE_TESTS",
    "ADMIN_ID": "10001",
    "BASE_URL": "https://bot.example.com",
    "WEBHOOK_SECRET": "offline_test_secret",
})

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, GetMe, SendMessage
from aiogram.types import Message, Update, User

from keyboards.kb import main_contact_kb
from utils import db


class RecordingSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.sent = []

    async def close(self):
        pass

    async def make_request(self, bot, method, timeout=None):
        if isinstance(method, GetMe):
            return User(id=bot.id, is_bot=True, first_name="Test bot", username="test_bot")
        if isinstance(method, AnswerCallbackQuery):
            return True
        if isinstance(method, SendMessage):
            self.sent.append(method)
            return Message(
                message_id=len(self.sent), date=datetime.now(timezone.utc),
                chat={"id": method.chat_id, "type": "private" if method.chat_id > 0 else "supergroup"},
                text=method.text,
            )
        raise AssertionError(f"Unexpected Telegram request: {type(method).__name__}")

    async def stream_content(self, url, headers=None, timeout=30, chunk_size=65536, raise_for_status=True):
        raise AssertionError("Tests must not download files")
        yield b""  # Make this an async generator, as required by BaseSession.


class BotRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session = RecordingSession()
        self.bot = Bot(os.environ["BOT_TOKEN"], session=self.session)
        self.dispatcher = Dispatcher()
        import handlers.admin_panel
        import handlers.start
        self.admin = importlib.reload(handlers.admin_panel)
        self.start = importlib.reload(handlers.start)
        self.dispatcher.include_router(self.admin.router)
        self.dispatcher.include_router(self.start.router)
        self.add_user = AsyncMock()
        self.get_user = AsyncMock(return_value={"telegram_id": 10002, "bot_open": True})
        self.update_access = AsyncMock()
        for target, replacement in (
            ("add_user", self.add_user),
            ("get_user_by_id", self.get_user),
            ("update_bot_open_status", self.update_access),
        ):
            patcher = patch.object(self.start, target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)

    async def asyncTearDown(self):
        await self.dispatcher.storage.close()
        await self.bot.session.close()

    async def feed(self, *, user_id=10002, chat=None, **fields):
        payload = {
            "message_id": 10, "date": 1700000000,
            "chat": chat or {"id": user_id, "type": "private"},
            "from": {"id": user_id, "is_bot": False, "first_name": "Alice <&>", "username": "alice"},
            **fields,
        }
        await self.dispatcher.feed_update(self.bot, Update.model_validate({"update_id": 1, "message": payload}))
        return self.session.sent[-1] if self.session.sent else None

    def assert_copies(self, sent, expected):
        actual = [button.copy_text.text for row in sent.reply_markup.inline_keyboard for button in row]
        self.assertEqual(actual, [str(value) for value in expected])

    async def test_modern_shared_user_routes_and_escapes_names(self):
        sent = await self.feed(users_shared={"request_id": 1, "users": [
            {"user_id": 90001, "first_name": "Bob <admin>", "username": "bob"},
        ]})
        self.assertIn("90001", sent.text)
        self.assertIn("Bob &lt;admin&gt;", sent.text)
        self.assertIn("@bob", sent.text)
        self.assert_copies(sent, [90001])

    async def test_shared_bot_has_bot_label(self):
        sent = await self.feed(users_shared={"request_id": 4, "users": [{"user_id": 90002}]})
        self.assertIn("🤖 Бот", sent.text)
        self.assert_copies(sent, [90002])

    async def test_private_group_without_username(self):
        sent = await self.feed(chat_shared={"request_id": 2, "chat_id": -100123, "title": "Private <group>"})
        self.assertIn("Private &lt;group&gt;", sent.text)
        self.assertIn("Username: не указан", sent.text)
        self.assert_copies(sent, [-100123])

    async def test_shared_channel(self):
        sent = await self.feed(chat_shared={"request_id": 3, "chat_id": -100124, "title": "Channel", "username": "channel"})
        self.assertIn("📢 Канал", sent.text)
        self.assert_copies(sent, [-100124])

    async def test_forwarded_user(self):
        sent = await self.feed(text="hello", forward_origin={
            "type": "user", "date": 1700000000,
            "sender_user": {"id": 30001, "is_bot": False, "first_name": "Sender"},
        })
        self.assert_copies(sent, [30001])

    async def test_forwarded_command_reports_source_not_recipient(self):
        sent = await self.feed(text="/id", forward_origin={
            "type": "user", "date": 1700000000,
            "sender_user": {"id": 30002, "is_bot": False, "first_name": "Sender"},
        })
        self.assert_copies(sent, [30002])

    async def test_forwarded_channel_post(self):
        sent = await self.feed(text="Post", forward_origin={
            "type": "channel", "date": 1700000000, "message_id": 20,
            "chat": {"id": -100555, "type": "channel", "title": "News"},
        })
        self.assert_copies(sent, [-100555])

    async def test_forwarded_message_on_behalf_of_chat(self):
        sent = await self.feed(text="Post", forward_origin={
            "type": "chat", "date": 1700000000,
            "sender_chat": {"id": -100556, "type": "supergroup", "title": "Group"},
        })
        self.assert_copies(sent, [-100556])

    async def test_hidden_forward_does_not_invent_id(self):
        sent = await self.feed(text="hello", forward_origin={
            "type": "hidden_user", "date": 1700000000, "sender_user_name": "Hidden",
        })
        self.assertIn("не передаёт его ID", sent.text)
        self.assertIsNotNone(sent.reply_markup.keyboard)

    async def test_id_in_private_chat(self):
        sent = await self.feed(text="/id")
        self.assertIn("Alice &lt;&amp;&gt;", sent.text)
        self.assert_copies(sent, [10002])

    async def test_existing_my_info_button(self):
        sent = await self.feed(text="🆔 MY INFO")
        self.assert_copies(sent, [10002])

    async def test_group_id_and_topic(self):
        sent = await self.feed(text="/id", chat={"id": -100200, "type": "supergroup", "title": "Forum"},
                               is_topic_message=True, message_thread_id=42)
        self.assert_copies(sent, [-100200, 42])
        self.get_user.assert_not_awaited()

    async def test_reply_reports_group_and_participant(self):
        sent = await self.feed(text="/id", chat={"id": -100200, "type": "supergroup", "title": "Group"},
                               reply_to_message={
                                   "message_id": 9, "date": 1700000000,
                                   "chat": {"id": -100200, "type": "supergroup", "title": "Group"},
                                   "from": {"id": 44444, "is_bot": False, "first_name": "Participant"},
                                   "text": "hello",
                               })
        self.assert_copies(sent, [-100200, 44444])

    async def test_anonymous_admin_uses_sender_chat(self):
        sent = await self.feed(text="/id", chat={"id": -100200, "type": "supergroup", "title": "Group"},
                               reply_to_message={
                                   "message_id": 9, "date": 1700000000,
                                   "chat": {"id": -100200, "type": "supergroup", "title": "Group"},
                                   "from": {"id": 1087968824, "is_bot": True, "first_name": "GroupAnonymousBot"},
                                   "sender_chat": {"id": -100200, "type": "supergroup", "title": "Group"},
                               })
        self.assert_copies(sent, [-100200, -100200])
        self.assertNotIn("1087968824", sent.text)

    async def test_addressed_id_command(self):
        sent = await self.feed(text="/id@test_bot", chat={"id": -100200, "type": "supergroup", "title": "Group"})
        self.assert_copies(sent, [-100200])

    async def test_subscription_gate_covers_manual_info_button(self):
        self.get_user.return_value = {"bot_open": False}
        sent = await self.feed(text="🆔 MY INFO")
        self.assertIn("подпишитесь", sent.text)
        self.assertIsNone(sent.reply_markup.inline_keyboard[0][0].copy_text)

    async def test_subscription_gate_covers_shared_and_forwarded_ids(self):
        self.get_user.return_value = None
        for fields in (
            {"users_shared": {"request_id": 1, "users": [{"user_id": 90001}]}},
            {"chat_shared": {"request_id": 2, "chat_id": -100123}},
            {"forward_origin": {"type": "hidden_user", "date": 1700000000, "sender_user_name": "Hidden"}},
            {"text": "/id"},
        ):
            with self.subTest(fields=fields):
                sent = await self.feed(**fields)
                self.assertIn("подпишитесь", sent.text)

    async def test_group_start_does_not_send_private_selection_keyboard(self):
        sent = await self.feed(text="/start", chat={"id": -100200, "type": "supergroup", "title": "Group"})
        self.assertIsNone(sent.reply_markup)
        self.add_user.assert_not_awaited()

    async def test_help_explains_privacy_and_copying(self):
        sent = await self.feed(text="/help")
        self.assertIn("скрытом авторе", sent.text)
        self.assertIn("копирования", sent.text)

    async def test_admin_menu_is_not_swallowed_by_fallback(self):
        sent = await self.feed(user_id=10001, text="⚙️ АДМИНКА")
        self.assertIn("админку", sent.text)

    async def test_forwarded_broadcast_draft_is_not_swallowed(self):
        state = self.dispatcher.fsm.get_context(bot=self.bot, chat_id=10001, user_id=10001)
        await state.set_state(self.admin.Form.start_broadcast)
        with patch.object(self.admin, "get_all_users", AsyncMock(return_value=[])), \
             patch.object(self.admin, "broadcast_message", AsyncMock(return_value=(0, 0))) as broadcast:
            await self.feed(user_id=10001, text="Announcement", forward_origin={
                "type": "channel", "date": 1700000000, "message_id": 20,
                "chat": {"id": -100555, "type": "channel", "title": "News"},
            })
            broadcast.assert_awaited_once()
            self.assertIn("Рассылка завершена", self.session.sent[-1].text)

    async def test_subscription_callback_creates_user_before_unlocking(self):
        with patch.object(self.start, "is_user_subscribed", AsyncMock(return_value=True)):
            await self.dispatcher.feed_update(self.bot, Update.model_validate({
                "update_id": 2,
                "callback_query": {
                    "id": "check1", "chat_instance": "instance", "data": "check_subscription",
                    "from": {"id": 10002, "is_bot": False, "first_name": "Alice"},
                    "message": {"message_id": 1, "date": 1700000000,
                                "chat": {"id": 10002, "type": "private"}, "text": "Subscribe"},
                },
            }))
        self.add_user.assert_awaited_once()
        self.update_access.assert_awaited_once_with(10002, bot_open=True)


class KeyboardTests(unittest.TestCase):
    def test_selection_buttons_use_modern_api_and_accept_private_groups(self):
        keyboard = main_contact_kb(10002)
        for button in keyboard.keyboard[0]:
            self.assertEqual(button.request_users.max_quantity, 1)
            self.assertTrue(button.request_users.request_name)
            self.assertTrue(button.request_users.request_username)
        group = keyboard.keyboard[1][0].request_chat
        self.assertIsNone(group.chat_has_username)
        self.assertTrue(group.request_title)


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_profile_refresh_preserves_subscription_access(self):
        original_connect = db.aiosqlite.connect
        with tempfile.TemporaryDirectory() as folder:
            database_path = str(Path(folder) / "bot.db")
            with patch.object(db.aiosqlite, "connect", side_effect=lambda *a, **kw: original_connect(database_path)):
                await db.initialize_database()
                await db.add_user(555, "old_name", "Old")
                await db.update_bot_open_status(555, True)
                await db.add_user(555, "new_name", "New")
                user = await db.get_user_by_id(555)
                self.assertTrue(user["bot_open"])
                self.assertEqual(user["username"], "new_name")


if __name__ == "__main__":
    unittest.main()
