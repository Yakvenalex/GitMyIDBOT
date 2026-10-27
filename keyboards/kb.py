from aiogram.types import (
    CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
    KeyboardButtonRequestChat, KeyboardButtonRequestUsers, ReplyKeyboardMarkup,
)

from create_bot import ADMIN_ID


def cancel_btn():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Или нажмите на 'ОТМЕНА' для отмены"
    )


def main_contact_kb(user_id: int):
    buttons = [
        [
            KeyboardButton(
                text="👤 USER ID",
                request_users=KeyboardButtonRequestUsers(
                    request_id=1,
                    user_is_bot=False,
                    max_quantity=1,
                    request_name=True,
                    request_username=True,
                )
            ),
            KeyboardButton(
                text="🤖 BOT ID",
                request_users=KeyboardButtonRequestUsers(
                    request_id=4,
                    user_is_bot=True,
                    max_quantity=1,
                    request_name=True,
                    request_username=True,
                )
            )
        ],
        [
            KeyboardButton(
                text="👥 GROUP ID",
                request_chat=KeyboardButtonRequestChat(
                    request_id=2,
                    chat_is_channel=False,
                    request_title=True,
                    request_username=True,
                )
            ),
            KeyboardButton(
                text="📢 CHANNEL ID",
                request_chat=KeyboardButtonRequestChat(
                    request_id=3,
                    chat_is_channel=True,
                    request_title=True,
                    request_username=True,
                )
            )
        ],
        [
            KeyboardButton(
                text="🆔 MY INFO",
            )
        ]
    ]

    if user_id == ADMIN_ID:
        buttons.append([
            KeyboardButton(
                text="⚙️ АДМИНКА",
            )
        ])

    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="По ком получим ID?"
    )

    return keyboard


def copy_ids_kb(items: list[tuple[str, int]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, copy_text=CopyTextButton(text=str(identifier)))]
        for label, identifier in items
    ])


def admin_kb():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton(text="📧 Рассылка", callback_data="admin_broadcast")]
        ]
    )
    return keyboard


def broadcast_kb():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_admin")],
            [
                InlineKeyboardButton(text="🚀 Начать рассылку", callback_data="start_broadcast")
            ]
        ]
    )
    return keyboard


def channels_kb(kb_list: list):
    inline_keyboard = []

    for channel_data in kb_list:
        label = channel_data.get('label')
        url = channel_data.get('url')

        # Проверка на наличие необходимых ключей
        if label and url:
            kb = [InlineKeyboardButton(text=label, url=url)]
            inline_keyboard.append(kb)

    # Добавление кнопки "Проверить подписку"
    inline_keyboard.append([InlineKeyboardButton(text="Проверить подписку", callback_data="check_subscription")])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
