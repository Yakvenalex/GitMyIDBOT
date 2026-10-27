"""HTML-safe identity cards for Telegram objects shared with the bot."""

from dataclasses import dataclass
from html import escape

from aiogram.types import (
    Chat, ChatShared, MessageOriginChannel, MessageOriginChat,
    MessageOriginHiddenUser, MessageOriginUser, SharedUser, User,
)


@dataclass(frozen=True)
class IdentityCard:
    title: str
    identifier: int
    name: str | None = None
    username: str | None = None

    def render(self) -> str:
        lines = [f"<b>{escape(self.title)}</b>", f"🆔 ID: <code>{self.identifier}</code>"]
        if self.name:
            lines.append(f"Название / имя: {escape(self.name)}")
        lines.append(f"Username: @{escape(self.username)}" if self.username else "Username: не указан")
        return "\n".join(lines)


def user_card(user: User) -> IdentityCard:
    return IdentityCard(
        "🤖 Бот" if user.is_bot else "👤 Пользователь",
        user.id, user.full_name, user.username,
    )


def shared_user_card(user: SharedUser, *, is_bot: bool) -> IdentityCard:
    name = " ".join(part for part in (user.first_name, user.last_name) if part) or None
    return IdentityCard("🤖 Бот" if is_bot else "👤 Пользователь", user.user_id, name, user.username)


def chat_card(chat: Chat) -> IdentityCard:
    title = {"channel": "📢 Канал", "supergroup": "👥 Группа", "group": "👥 Группа"}.get(
        chat.type, "💬 Чат"
    )
    return IdentityCard(title, chat.id, chat.title or chat.full_name, chat.username)


def shared_chat_card(chat: ChatShared) -> IdentityCard:
    return IdentityCard(
        "👥 Группа" if chat.request_id == 2 else "📢 Канал",
        chat.chat_id, chat.title, chat.username,
    )


def forwarded_card(
    origin: MessageOriginUser | MessageOriginHiddenUser | MessageOriginChat | MessageOriginChannel,
) -> IdentityCard | None:
    if isinstance(origin, MessageOriginUser):
        return user_card(origin.sender_user)
    if isinstance(origin, MessageOriginChat):
        return chat_card(origin.sender_chat)
    if isinstance(origin, MessageOriginChannel):
        return chat_card(origin.chat)
    # Telegram deliberately omits the ID when the sender hides their identity.
    return None
