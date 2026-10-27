from html import escape

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import CallbackQuery, Message

from create_bot import kb_list
from keyboards.kb import channels_kb, copy_ids_kb, main_contact_kb
from utils.cards import chat_card, forwarded_card, shared_chat_card, shared_user_card, user_card
from utils.db import add_user, get_user_by_id, update_bot_open_status
from utils.utils import is_user_subscribed

router = Router()
PRIVATE = F.chat.type == ChatType.PRIVATE

HELP_TEXT = (
    "<b>🆔 Как узнать Telegram ID</b>\n\n"
    "• /id — ваши данные; в группе — ID группы и текущей темы.\n"
    "• Ответьте командой /id на сообщение участника группы, чтобы узнать его ID.\n"
    "• В личном чате выберите пользователя, бота, группу или канал кнопками ниже. "
    "Поддерживаются и закрытые группы.\n"
    "• Перешлите мне сообщение или пост канала — покажу данные источника, "
    "если Telegram их передал. При скрытом авторе ID недоступен; "
    "используйте кнопку «👤 USER ID».\n\n"
    "Под каждым результатом есть кнопка копирования ID.\n"
    "/start — открыть меню, /help — эта справка."
)


async def ensure_private_access(message: Message) -> bool:
    """Honor the existing subscription gate for every private ID entry point."""
    if message.from_user is None:
        return False
    user = message.from_user
    await add_user(user.id, user.username, user.first_name)
    data = await get_user_by_id(user.id)
    if not kb_list or (data and data.get("bot_open")):
        return True
    await message.answer(
        "Для пользования ботом подпишитесь на каналы и нажмите «Проверить подписку»:",
        reply_markup=channels_kb(kb_list),
    )
    return False


@router.message(CommandStart(), PRIVATE, F.forward_origin.is_(None), StateFilter(None))
async def start(message: Message):
    if await ensure_private_access(message):
        await message.answer(
            "🆔 Выберите, чей ID узнать, или перешлите сообщение.\n"
            "Ваши данные: /id · Инструкция: /help",
            reply_markup=main_contact_kb(message.from_user.id),
        )


@router.message(CommandStart(), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}), F.forward_origin.is_(None))
async def group_start(message: Message):
    await message.answer(
        "Отправьте /id, чтобы узнать ID группы и темы. "
        "Ответьте /id на сообщение участника, чтобы узнать его ID."
    )


@router.message(Command("help"), F.forward_origin.is_(None), StateFilter(None))
async def help_command(message: Message):
    keyboard = main_contact_kb(message.from_user.id) if message.chat.type == ChatType.PRIVATE else None
    await message.answer(HELP_TEXT, reply_markup=keyboard)


@router.callback_query(F.data == "check_subscription")
async def check_subs_func(call: CallbackQuery):
    await call.answer("Проверяю подписки…")
    if not isinstance(call.message, Message) or call.message.chat.type != ChatType.PRIVATE:
        return
    await add_user(call.from_user.id, call.from_user.username, call.from_user.first_name)
    for channel in kb_list:
        if not await is_user_subscribed(channel["url"], call.from_user.id):
            await call.message.answer(
                f"❌ Не удалось подтвердить подписку на канал «{escape(channel['label'])}». "
                "Подпишитесь и попробуйте ещё раз.",
                reply_markup=channels_kb(kb_list),
            )
            return
    await update_bot_open_status(call.from_user.id, bot_open=True)
    await call.message.answer(
        "✅ Доступ открыт! Выберите, чей ID узнать, или перешлите сообщение.",
        reply_markup=main_contact_kb(call.from_user.id),
    )


@router.message(Command("id"), F.forward_origin.is_(None), StateFilter(None))
async def id_command(message: Message):
    if message.chat.type == ChatType.PRIVATE:
        if await ensure_private_access(message):
            card = user_card(message.from_user)
            await message.answer(card.render(), reply_markup=copy_ids_kb([("📋 Скопировать ID", card.identifier)]))
        return

    card = chat_card(message.chat)
    text = card.render()
    copies = [("📋 ID чата", card.identifier)]
    if message.message_thread_id is not None:
        text += f"\n🧵 ID темы: <code>{message.message_thread_id}</code>"
        copies.append(("📋 ID темы", message.message_thread_id))

    reply = message.reply_to_message
    if reply:
        # Anonymous administrators speak on behalf of a chat, not the fake sender user.
        target = chat_card(reply.sender_chat) if reply.sender_chat else (
            user_card(reply.from_user) if reply.from_user else None
        )
        if target:
            text += "\n\n<b>Автор сообщения</b>\n" + target.render()
            copies.append(("📋 ID автора сообщения", target.identifier))

    await message.answer(text, reply_markup=copy_ids_kb(copies))


@router.message(PRIVATE, F.text == "🆔 MY INFO", F.forward_origin.is_(None), StateFilter(None))
async def handle_my_id(message: Message):
    await id_command(message)


@router.message(PRIVATE, F.users_shared, StateFilter(None))
async def handle_users(message: Message):
    if not await ensure_private_access(message):
        return
    shared = message.users_shared
    if shared.request_id not in (1, 4):
        return
    for user in shared.users:
        card = shared_user_card(user, is_bot=shared.request_id == 4)
        await message.answer(card.render(), reply_markup=copy_ids_kb([("📋 Скопировать ID", card.identifier)]))


@router.message(PRIVATE, F.chat_shared, StateFilter(None))
async def handle_chat_or_channel(message: Message):
    if not await ensure_private_access(message) or message.chat_shared.request_id not in (2, 3):
        return
    card = shared_chat_card(message.chat_shared)
    await message.answer(card.render(), reply_markup=copy_ids_kb([("📋 Скопировать ID", card.identifier)]))


@router.message(PRIVATE, F.forward_origin, StateFilter(None))
async def handle_forward(message: Message):
    if not await ensure_private_access(message):
        return
    card = forwarded_card(message.forward_origin)
    if card is None:
        await message.answer(
            "🔒 Автор скрыл данные при пересылке: Telegram не передаёт его ID.\n"
            "Попробуйте выбрать человека кнопкой «👤 USER ID».",
            reply_markup=main_contact_kb(message.from_user.id),
        )
        return
    await message.answer(card.render(), reply_markup=copy_ids_kb([("📋 Скопировать ID", card.identifier)]))


@router.message(PRIVATE, F.text, StateFilter(None))
async def unknown_message(message: Message):
    await message.answer(
        "Чтобы узнать ID, используйте /id, кнопки меню или перешлите сообщение.\n"
        "Подробная инструкция: /help",
        reply_markup=main_contact_kb(message.from_user.id),
    )
