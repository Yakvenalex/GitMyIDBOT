from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from create_bot import ADMIN_ID
from utils.db import get_all_users
from keyboards.kb import admin_kb, cancel_btn
from utils.utils import broadcast_message

router = Router()


class Form(StatesGroup):
    start_broadcast = State()


@router.message((F.from_user.id == ADMIN_ID) & (F.text == '⚙️ АДМИНКА'))
async def admin_handler(message: Message):
    await message.answer('Вам открыт доступ в админку! Выберите действие👇', reply_markup=admin_kb())


@router.callback_query((F.from_user.id == ADMIN_ID) & (F.data == 'admin_users'))
async def admin_users_handler(call: CallbackQuery):
    await call.answer('Готовлю список пользователей')
    users_data = await get_all_users()

    text = f'В базе данных {len(users_data)}. Вот информация по ним:\n\n'

    for user in users_data:
        text += f'<code>{user["telegram_id"]} - {user["first_name"]}</code>\n'

    await call.message.answer(text, reply_markup=admin_kb())


@router.callback_query((F.from_user.id == ADMIN_ID) & (F.data == 'admin_broadcast'))
async def admin_broadcast_handler(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer(
        'Отправьте любое сообщение, а я его перехвачу и перешлю всем пользователям с базы данных',
        reply_markup=cancel_btn()
    )
    await state.set_state(Form.start_broadcast)


@router.message(F.content_type.in_({'text', 'photo', 'document', 'video', 'audio'}), Form.start_broadcast)
async def universe_broadcast(message: Message, state: FSMContext):
    users_data = await get_all_users()
    await message.answer(f'Начинаю рассылку на {len(users_data)} пользователей.')

    # Определяем параметры для рассылки в зависимости от типа сообщения
    content_type = message.content_type

    if content_type == ContentType.TEXT and message.text == '❌ Отмена':
        await state.clear()
        await message.answer('Рассылка отменена!', reply_markup=admin_kb())
        return

    good_send, bad_send = await broadcast_message(
        users_data=users_data,
        text=message.text if content_type == ContentType.TEXT else None,
        photo_id=message.photo[-1].file_id if content_type == ContentType.PHOTO else None,
        document_id=message.document.file_id if content_type == ContentType.DOCUMENT else None,
        video_id=message.video.file_id if content_type == ContentType.VIDEO else None,
        audio_id=message.audio.file_id if content_type == ContentType.AUDIO else None,
        caption=message.caption,
        content_type=content_type
    )

    await state.clear()
    await message.answer(f'Рассылка завершена. Сообщение получило <b>{good_send}</b>, '
                         f'НЕ получило <b>{bad_send}</b> пользователей.', reply_markup=admin_kb())
