import asyncio
from aiogram.enums import ContentType, ChatMemberStatus
from create_bot import bot
from keyboards.kb import main_contact_kb


async def is_user_subscribed(channel_url: str, telegram_id: int) -> bool:
    try:
        # Получаем username канала из URL
        channel_username = channel_url.split('/')[-1]

        # Получаем информацию о пользователе в канале
        member = await bot.get_chat_member(chat_id=f"@{channel_username}", user_id=telegram_id)

        # Проверяем статус пользователя
        if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]:
            return True
        else:
            return False
    except Exception as e:
        # Если возникла ошибка (например, пользователь не найден или бот не имеет доступа к каналу)
        print(f"Ошибка при проверке подписки: {e}")
        return False


async def broadcast_message(users_data: list, text: str = None, photo_id: int = None, document_id: int = None,
                            video_id: int = None, audio_id: int = None, caption: str = None, content_type: str = None):
    good_send = 0
    bad_send = 0
    for user in users_data:
        try:
            chat_id = user.get('telegram_id')
            if content_type == ContentType.TEXT:
                await bot.send_message(chat_id=chat_id, text=text, reply_markup=main_contact_kb(chat_id))
            elif content_type == ContentType.PHOTO:
                await bot.send_photo(chat_id=chat_id, photo=photo_id, caption=caption,
                                     reply_markup=main_contact_kb(chat_id))
            elif content_type == ContentType.DOCUMENT:
                await bot.send_document(chat_id=chat_id, document=document_id, caption=caption,
                                        reply_markup=main_contact_kb(chat_id))
            elif content_type == ContentType.VIDEO:
                await bot.send_video(chat_id=chat_id, video=video_id, caption=caption,
                                     reply_markup=main_contact_kb(chat_id))
            elif content_type == ContentType.AUDIO:
                await bot.send_audio(chat_id=chat_id, audio=audio_id, caption=caption,
                                     reply_markup=main_contact_kb(chat_id))
            good_send += 1
        except Exception as e:
            print(e)
            bad_send += 1
        finally:
            await asyncio.sleep(1)
    return good_send, bad_send
