# suggestion_complaint.py fayli (Taklif va shikoyatlar bo'limi)

import os
import logging
from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from states import MainForm, SuggestionForm
from keyboards import texts, get_user_keyboard, get_admin_main_keyboard
import database as db

router = Router()

# Sozlamalar
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
    
    # Agar telefon yo'q bo'lsa, foydalanuvchidan kontakt so'rash imkoniyati
    if phone_number == "Kiritilmagan":
        contact_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=texts[lang]['button_share_contact'], request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(texts[lang]['ask_contact'], reply_markup=contact_keyboard)
        # Xabarni state'ga vaqtincha saqlab turamiz
        await state.update_data(pending_suggestion_text=suggestion_text)
        return

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
            sent_message = await bot.send_message(HR_GROUP_ID, hr_notification, parse_mode="Markdown")
            logging.info(f"Taklif/shikoyat HR guruhiga yuborildi. User ID: {user_id}")
            # HR guruhidagi xabar ID sini bazaga saqlash
            await db.save_suggestion_message(user_id, sent_message.message_id, lang)
        except Exception as e:
            logging.error(f"HR guruhiga taklif/shikoyat yuborishda xatolik: {e}")
    
    # Foydalanuvchiga tasdiq xabari
    await message.answer(texts[lang]['suggestion_thanks'])
    
    # Asosiy menyuga qaytish
    if await db.is_admin(user_id):
        keyboard = get_admin_main_keyboard(lang)
    else:
        keyboard = get_user_keyboard(lang)
    
    await message.answer(texts[lang]['welcome_menu'], reply_markup=keyboard)
    await state.set_state(MainForm.main_menu)


@router.message(SuggestionForm.waiting_text, F.contact)
async def process_suggestion_contact(message: Message, state: FSMContext, bot: Bot):
    """Agar telefon so'ralgan bo'lsa, kontakt kelganda HRga xabarni yuborish"""
    lang = await get_user_lang(state)
    user_data = await state.get_data()
    suggestion_text = user_data.get('pending_suggestion_text', '')

    # Raqamni bazaga saqlab qo'yamiz
    try:
        await db.update_user_phone_number(message.from_user.id, message.contact.phone_number)
    except Exception:
        pass

    full_name = message.from_user.full_name
    username = message.from_user.username
    phone_number = message.contact.phone_number or "Kiritilmagan"

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
            sent_message = await bot.send_message(HR_GROUP_ID, hr_notification, parse_mode="Markdown")
            # HR guruhidagi xabar ID sini bazaga saqlash
            await db.save_suggestion_message(message.from_user.id, sent_message.message_id, lang)
        except Exception as e:
            logging.error(f"HR guruhiga taklif/shikoyat yuborishda xatolik: {e}")

    await message.answer(texts[lang]['suggestion_thanks'], reply_markup=ReplyKeyboardRemove())

    if await db.is_admin(message.from_user.id):
        keyboard = get_admin_main_keyboard(lang)
    else:
        keyboard = get_user_keyboard(lang)
    await message.answer(texts[lang]['welcome_menu'], reply_markup=keyboard)
    await state.set_state(MainForm.main_menu)


# --- HR GURUHIDA REPLY QILISH FUNKSIYASI ---

@router.message(F.reply_to_message)
async def handle_hr_group_reply(message: Message, bot: Bot):
    """HR guruhida bot xabariga reply qilinganda ishga tushadi"""
    
    # HR_GROUP_ID sozlangan bo'lishi kerak
    if not HR_GROUP_ID:
        return
    
    # Faqat HR guruhidan kelgan xabarlarni qabul qilamiz
    if str(message.chat.id) != str(HR_GROUP_ID):
        return
    
    # Faqat text xabarlarni qabul qilamiz
    if not message.text:
        return
    
    # Reply qilingan xabar botdan bo'lishi kerak
    if not message.reply_to_message.from_user.is_bot:
        return
    
    try:
        # Reply qilingan xabar ID sini olamiz
        replied_message_id = message.reply_to_message.message_id
        
        # Bazadan asl foydalanuvchi ma'lumotlarini topamiz
        suggestion = await db.get_suggestion_by_hr_message(replied_message_id)
        
        if not suggestion:
            return  # Agar topilmasa, hech narsa qilmaymiz
        
        # Asl foydalanuvchi ma'lumotlarini olamiz
        user_id = suggestion.user_id
        user_lang = suggestion.user_lang
        
        # Javob matnini tayyorlaymiz
        reply_text = f"{texts[user_lang]['hr_reply_prefix']} {message.text}"
        
        # Foydalanuvchiga javob yuboramiz
        await bot.send_message(chat_id=user_id, text=reply_text)
        logging.info(f"HR javobi foydalanuvchiga yuborildi. User ID: {user_id}, Reply: {message.text[:50]}")
        
    except Exception as e:
        logging.error(f"HR guruh javobini ishlashda xatolik: {e}")

