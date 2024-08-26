from aiogram.types import ReplyKeyboardMarkup, KeyboardButtonRequestUser, KeyboardButton, KeyboardButtonRequestChat, \
    InlineKeyboardMarkup, InlineKeyboardButton

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
                request_user=KeyboardButtonRequestUser(
                    request_id=1,
                    user_is_bot=False
                )
            ),
            KeyboardButton(
                text="🤖 BOT ID",
                request_user=KeyboardButtonRequestUser(
                    request_id=4,
                    user_is_bot=True
                )
            )
        ],
        [
            KeyboardButton(
                text="👥 GROUP ID",
                request_chat=KeyboardButtonRequestChat(
                    request_id=2,
                    chat_is_channel=False,  # Включает только обычные группы (не каналы)
                    chat_has_username=True
                )
            ),
            KeyboardButton(
                text="📢 CHANNEL ID",
                request_chat=KeyboardButtonRequestChat(
                    request_id=3,
                    chat_is_channel=True  # Включает только каналы
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
