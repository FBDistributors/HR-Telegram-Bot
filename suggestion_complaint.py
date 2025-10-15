# suggestion_complaint.py fayli (Taklif va shikoyatlar bo'limi)

import os
import logging
from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from states import MainForm, SuggestionForm
from keyboards import texts, get_user_keyboard, get_admin_main_keyboard
import database as db

router = Router()

# Sozlamalar
ADMIN_ID = os.getenv("ADMIN_ID")
HR_GROUP_ID = os.getenv("HR_GROUP_ID")


async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')


# --- TAKLIF VA SHIKOYATLAR BO'LIMI ---

@router.message(F.text.in_([texts['uz']['suggestion_button'], texts['ru']['suggestion_button']]))
async def handle_suggestion_button(message: Message, state: FSMContext):
    """Taklif va shikoyatlar tugmasi bosilganda"""
    lang = await get_user_lang(state)
    await message.answer(texts[lang]['ask_suggestion_text'])
    await state.set_state(SuggestionForm.waiting_text)


@router.message(Command("suggest"))
async def handle_suggestion_command(message: Message, state: FSMContext):
    """Alternative entry via /suggest command"""
    lang = await get_user_lang(state)
    await message.answer(texts[lang]['ask_suggestion_text'])
    await state.set_state(SuggestionForm.waiting_text)


@router.message(SuggestionForm.waiting_text, F.text)
async def process_suggestion_text(message: Message, state: FSMContext, bot: Bot):
    """Taklif/shikoyat matnini qabul qilish va HR guruhiga yuborish"""
    lang = await get_user_lang(state)
    suggestion_text = message.text
    
    # Foydalanuvchi ma'lumotlarini olish
    full_name = message.from_user.full_name
    username = message.from_user.username
    user_id = message.from_user.id
    
    # Telefon raqamini bazadan olish (agar mavjud bo'lsa)
    phone_number = "Kiritilmagan"
    try:
        # Users jadvalidan telefon raqamini topish
        from sqlalchemy import select
        from database import User, async_session_maker
        
        async with async_session_maker() as session:
            result = await session.execute(select(User).filter(User.user_id == user_id))
            user = result.scalars().first()
            if user and user.phone_number:
                phone_number = user.phone_number
    except Exception as e:
        logging.error(f"Telefon raqamni olishda xatolik: {e}")
    
    # HR guruhiga yuborish
    if HR_GROUP_ID:
        hr_notification = (
            f"🔔 **{texts[lang]['hr_new_suggestion']}**\n\n"
            f"👤 **FIO:** {full_name}"
        )
        
        if username:
            hr_notification += f" (@{username})"
        
        hr_notification += (
            f"\n📱 **Telefon:** {phone_number}\n"
            f"-------------------\n"
            f"📝 **Xabar:**\n{suggestion_text}"
        )
        
        try:
            await bot.send_message(HR_GROUP_ID, hr_notification, parse_mode="Markdown")
            logging.info(f"Taklif/shikoyat HR guruhiga yuborildi. User ID: {user_id}")
        except Exception as e:
            logging.error(f"HR guruhiga taklif/shikoyat yuborishda xatolik: {e}")
    
    # Foydalanuvchiga tasdiq xabari
    await message.answer(texts[lang]['suggestion_thanks'])
    
    # Asosiy menyuga qaytish
    if str(user_id) == ADMIN_ID:
        keyboard = get_admin_main_keyboard(lang)
    else:
        keyboard = get_user_keyboard(lang)
    
    await message.answer(texts[lang]['welcome_menu'], reply_markup=keyboard)
    await state.set_state(MainForm.main_menu)

