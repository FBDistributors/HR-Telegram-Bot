# suggestion_complaint.py fayli (Taklif va shikoyatlar bo'limi)

import os
import logging
from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from states import MainForm, SuggestionForm
from keyboards import texts, get_user_keyboard, get_admin_main_keyboard, get_external_user_keyboard, get_employee_keyboard
import database as db

router = Router()

# Sozlamalar
HR_GROUP_ID = os.getenv("HR_GROUP_ID")


async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')


# --- TAKLIF VA SHIKOYATLAR BO'LIMI ---

@router.message(F.text.in_([texts['uz']['suggestion_button'], texts['ru']['suggestion_button'],
                            texts['uz']['support_center_button'], texts['ru']['support_center_button']]))
async def handle_suggestion_button(message: Message, state: FSMContext):
    """Taklif va shikoyatlar yoki Qo'llab quvvatlash markazi tugmasi bosilganda"""
    lang = await get_user_lang(state)
    user_data = await state.get_data()
    user_type = user_data.get('user_type', 'external')
    
    # Taklif/shikoyat tanlash
    type_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts[lang]['suggestion_type_button'], callback_data="suggestion_type_suggestion")],
        [InlineKeyboardButton(text=texts[lang]['complaint_type_button'], callback_data="suggestion_type_complaint")]
    ])
    
    await message.answer(texts[lang]['ask_suggestion_type'], reply_markup=type_keyboard)
    await state.set_state(SuggestionForm.type_selection)


@router.callback_query(SuggestionForm.type_selection, F.data.startswith('suggestion_type_'))
async def process_suggestion_type_selection(callback: CallbackQuery, state: FSMContext):
    """Taklif yoki shikoyat tanlash"""
    suggestion_type = callback.data.split('_')[2]  # 'suggestion' yoki 'complaint'
    lang = await get_user_lang(state)
    
    await callback.message.delete()
    
    if suggestion_type == 'suggestion':
        await callback.message.answer(texts[lang]['ask_suggestion_text'])
        await state.set_state(SuggestionForm.waiting_suggestion)
    else:
        await callback.message.answer(texts[lang]['ask_complaint_text'])
        await state.set_state(SuggestionForm.waiting_complaint)
    
    await callback.answer()


@router.message(SuggestionForm.waiting_suggestion, F.text)
async def process_suggestion_text(message: Message, state: FSMContext, bot: Bot):
    """Taklif matnini qabul qilish va HR guruhiga yuborish"""
    lang = await get_user_lang(state)
    suggestion_text = message.text
    user_data = await state.get_data()
    user_type = user_data.get('user_type', 'external')
    user_id = message.from_user.id
    
    # HR guruhiga yuborish
    if HR_GROUP_ID:
        hr_notification = f"🆕 **{texts[lang]['hr_new_suggestion']}**\n\n"
        
        if user_type == 'employee':
            # Xodimlar uchun to'liq ma'lumot (employees jadvalidan)
            employee = await db.get_employee_by_telegram_id(user_id)
            if employee:
                hr_notification += f"👤 **FIO:** {employee.full_name}\n"
                hr_notification += f"💼 **Lavozim:** {employee.position or 'Kiritilmagan'}\n"
                hr_notification += f"📱 **Telefon:** {employee.phone_number}\n"
            else:
                # Agar employees jadvalida topilmasa, Telegram ma'lumotlaridan foydalanamiz
                hr_notification += f"👤 **FIO:** {message.from_user.full_name}\n"
                if message.from_user.username:
                    hr_notification += f"📱 **Username:** @{message.from_user.username}\n"
        else:
            # Tashqi shaxslar uchun to'liq ma'lumot
            full_name = message.from_user.full_name
            username = message.from_user.username
            
            # Telefon raqamni bazadan olish
    phone_number = "Kiritilmagan"
    try:
        from sqlalchemy import select
        from database import User, async_session_maker
        
        async with async_session_maker() as session:
            result = await session.execute(select(User).filter(User.user_id == user_id))
            user = result.scalars().first()
            if user and user.phone_number:
                phone_number = user.phone_number
    except Exception as e:
        logging.error(f"Telefon raqamni olishda xatolik: {e}")
    
            hr_notification += f"👤 **FIO:** {full_name}\n"
        if username:
                hr_notification += f"📱 **Username:** @{username}\n"
            hr_notification += f"📞 **Telefon:** {phone_number}\n"
        
        hr_notification += f"\n💬 **Taklif matni:**\n\"{suggestion_text}\"\n\n"
        hr_notification += f"**{texts[lang]['hr_reply_instruction']}**"
        
        try:
            sent_message = await bot.send_message(HR_GROUP_ID, hr_notification, parse_mode="Markdown")
            logging.info(f"Taklif HR guruhiga yuborildi. User ID: {user_id}, Type: {user_type}")
            await db.save_suggestion_message(user_id, sent_message.message_id, lang, suggestion_text)
        except Exception as e:
            logging.error(f"HR guruhiga taklif yuborishda xatolik: {e}")
    
    # Foydalanuvchiga tasdiq xabari
    await message.answer(texts[lang]['suggestion_thanks'])
    
    # Asosiy menyuga qaytish
    await show_main_menu_back(message, state, user_id, lang)


@router.message(SuggestionForm.waiting_complaint, F.text)
async def process_complaint_text(message: Message, state: FSMContext, bot: Bot):
    """Shikoyat matnini qabul qilish va HR guruhiga yuborish"""
    lang = await get_user_lang(state)
    complaint_text = message.text
    user_data = await state.get_data()
    user_type = user_data.get('user_type', 'external')
    user_id = message.from_user.id
    
    # HR guruhiga yuborish
    if HR_GROUP_ID:
        if user_type == 'employee':
            # Xodimlar uchun anonim shikoyat
            hr_notification = f"🔔 **{texts[lang]['hr_anonymous_complaint']}**\n\n"
            hr_notification += f"⚠️ **{texts[lang]['hr_complaint_text']}**\n\"{complaint_text}\"\n\n"
            hr_notification += f"**{texts[lang]['hr_reply_instruction']}**"
        else:
            # Tashqi shaxslar uchun to'liq ma'lumot
            hr_notification = f"🔔 **{texts[lang]['hr_new_complaint']}**\n\n"

    full_name = message.from_user.full_name
    username = message.from_user.username
            
            # Telefon raqamni bazadan olish
            phone_number = "Kiritilmagan"
            try:
                from sqlalchemy import select
                from database import User, async_session_maker
                
                async with async_session_maker() as session:
                    result = await session.execute(select(User).filter(User.user_id == user_id))
                    user = result.scalars().first()
                    if user and user.phone_number:
                        phone_number = user.phone_number
            except Exception as e:
                logging.error(f"Telefon raqamni olishda xatolik: {e}")
            
            hr_notification += f"👤 **FIO:** {full_name}\n"
        if username:
                hr_notification += f"📱 **Username:** @{username}\n"
            hr_notification += f"📞 **Telefon:** {phone_number}\n"
            hr_notification += f"\n⚠️ **Shikoyat matni:**\n\"{complaint_text}\"\n\n"
            hr_notification += f"**{texts[lang]['hr_reply_instruction']}**"
        
        try:
            sent_message = await bot.send_message(HR_GROUP_ID, hr_notification, parse_mode="Markdown")
            logging.info(f"Shikoyat HR guruhiga yuborildi. User ID: {user_id}, Type: {user_type}")
            await db.save_suggestion_message(user_id, sent_message.message_id, lang, complaint_text)
        except Exception as e:
            logging.error(f"HR guruhiga shikoyat yuborishda xatolik: {e}")

    # Foydalanuvchiga tasdiq xabari
    await message.answer(texts[lang]['suggestion_thanks'])
    
    # Asosiy menyuga qaytish
    await show_main_menu_back(message, state, user_id, lang)


async def show_main_menu_back(message: Message, state: FSMContext, user_id: int, lang: str):
    """Foydalanuvchi turiga qarab asosiy menyuga qaytish"""
    user_data = await state.get_data()
    user_type = user_data.get('user_type', 'external')

    if await db.is_admin(user_id):
        keyboard = get_admin_main_keyboard(lang)
    elif user_type == 'employee':
        keyboard = get_employee_keyboard(lang)
    else:
        keyboard = get_external_user_keyboard(lang)
    
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
        
        # Original xabar matnini olish (uzunligini cheklash)
        original_text = suggestion.original_text or "Xabar"
        if len(original_text) > 50:
            original_text = original_text[:50] + "..."
        
        # Javob matnini tayyorlaymiz (original kontekst bilan)
        reply_header = texts[user_lang]['hr_reply_to_suggestion'].format(original=original_text)
        reply_text = f"{reply_header}\n\n{texts[user_lang]['hr_reply_prefix']} {message.text}"
        
        # Foydalanuvchiga javob yuboramiz
        await bot.send_message(chat_id=user_id, text=reply_text)
        logging.info(f"HR javobi foydalanuvchiga yuborildi. User ID: {user_id}, Reply: {message.text[:50]}")
        
    except Exception as e:
        logging.error(f"HR guruh javobini ishlashda xatolik: {e}")
