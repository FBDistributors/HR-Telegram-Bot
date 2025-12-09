# appsheet_issues.py fayli (AppSheet muammolari bo'limi)

import os
import logging
from aiogram import Bot, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from states import MainForm, AppSheetForm
from keyboards import texts, get_employee_keyboard, get_admin_main_keyboard
import database as db

router = Router()

# Sozlamalar
HR_GROUP_ID = os.getenv("HR_GROUP_ID")


async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')


# --- APPSHEET MUAMMOLARI BO'LIMI ---

@router.message(F.text.in_([texts['uz']['appsheet_issues_button'], texts['ru']['appsheet_issues_button']]))
async def handle_appsheet_issues_button(message: Message, state: FSMContext):
    """AppSheet muammolari tugmasi bosilganda"""
    lang = await get_user_lang(state)
    await message.answer(texts[lang]['appsheet_ask_name_department'])
    await state.set_state(AppSheetForm.name_department)


@router.message(AppSheetForm.name_department, F.text)
async def process_name_department(message: Message, state: FSMContext):
    """Ism, familya va ish joyini qabul qilish"""
    lang = await get_user_lang(state)
    name_department = message.text
    
    # State'ga saqlaymiz
    await state.update_data(name_department=name_department)
    
    # Keyingi bosqichga o'tamiz
    await message.answer(texts[lang]['appsheet_ask_problem'])
    await state.set_state(AppSheetForm.problem_description)


@router.message(AppSheetForm.problem_description, F.text)
async def process_problem_text(message: Message, state: FSMContext):
    """Muammo matnini qabul qilish"""
    lang = await get_user_lang(state)
    problem_text = message.text
    
    # State'ga saqlaymiz
    await state.update_data(problem_text=problem_text, problem_audio=None)
    
    # To'g'ridan-to'g'ri rasm so'ramiz (audio so'ralmaydi)
    await message.answer(texts[lang]['appsheet_ask_photo'])
    await state.set_state(AppSheetForm.problem_photo)


@router.message(AppSheetForm.problem_description, F.voice | F.audio)
async def process_problem_audio(message: Message, state: FSMContext):
    """Muammo audiosini qabul qilish"""
    lang = await get_user_lang(state)
    
    # Audio fayl ID va turini saqlaymiz
    if message.voice:
        audio_file_id = message.voice.file_id
        audio_type = 'voice'
    else:
        audio_file_id = message.audio.file_id
        audio_type = 'audio'
    
    # State'ga saqlaymiz
    await state.update_data(problem_audio=audio_file_id, problem_audio_type=audio_type, problem_text=None)
    
    # To'g'ridan-to'g'ri rasm so'ramiz (matn so'ralmaydi)
    await message.answer(texts[lang]['appsheet_ask_photo'])
    await state.set_state(AppSheetForm.problem_photo)


@router.message(AppSheetForm.problem_photo, F.photo)
async def process_problem_photo(message: Message, state: FSMContext, bot: Bot):
    """Muammo rasmini qabul qilish va HR guruhiga yuborish"""
    lang = await get_user_lang(state)
    user_data = await state.get_data()
    user_id = message.from_user.id
    
    name_department = user_data.get('name_department', 'Kiritilmagan')
    problem_text = user_data.get('problem_text')
    problem_audio = user_data.get('problem_audio')
    problem_audio_type = user_data.get('problem_audio_type', 'voice')
    photo_file_id = message.photo[-1].file_id  # Eng yuqori sifatli rasm
    
    # Foydalanuvchi ma'lumotlarini olish
    full_name = message.from_user.full_name
    username = message.from_user.username
    
    # Employees jadvalidan qo'shimcha ma'lumotlar
    employee = await db.get_employee_by_telegram_id(user_id)
    employee_info = ""
    if employee:
        employee_info = f"💼 <b>Lavozim:</b> {employee.position or 'Kiritilmagan'}\n"
        if employee.phone_number:
            employee_info += f"📞 <b>Telefon:</b> {employee.phone_number}\n"
    
    # HR guruhiga yuborish
    if HR_GROUP_ID:
        hr_notification = f"📱 <b>{texts[lang]['hr_new_appsheet_issue']}</b>\n\n"
        hr_notification += f"👤 <b>FIO:</b> {full_name}\n"
        if username:
            hr_notification += f"📱 <b>Username:</b> @{username}\n"
        if employee_info:
            hr_notification += employee_info
        hr_notification += f"\n📝 <b>Ism, familya va ish joyi:</b>\n{name_department}\n"
        hr_notification += f"\n⚠️ <b>Muammo:</b>\n"
        
        if problem_text:
            hr_notification += f"💬 <b>Matn:</b>\n{problem_text}\n"
        if problem_audio:
            hr_notification += f"🎤 <b>Audio yuborilgan</b>\n"
        
        hr_notification += f"\n📸 <b>Rasm yuborilgan</b>"
        hr_notification += f"\n\n{texts[lang]['hr_reply_instruction']}"
        
        # Original text ni tayyorlash (reply uchun)
        original_text = ""
        if problem_text:
            original_text = problem_text
        elif problem_audio:
            original_text = "Audio yuborilgan"
        else:
            original_text = "Rasm yuborilgan"
        
        try:
            # Matn xabarini yuboramiz
            sent_message = await bot.send_message(HR_GROUP_ID, hr_notification, parse_mode="HTML")
            
            # HR xabar ID sini va original text ni bazaga saqlash (reply uchun)
            await db.save_suggestion_message(user_id, sent_message.message_id, lang, original_text)
            
            # Audio yuborish (agar bo'lsa)
            if problem_audio:
                if problem_audio_type == 'voice':
                    await bot.send_voice(HR_GROUP_ID, problem_audio)
                else:
                    await bot.send_audio(HR_GROUP_ID, problem_audio)
            
            # Rasm yuborish
            await bot.send_photo(HR_GROUP_ID, photo_file_id)
            
            logging.info(f"AppSheet muammosi HR guruhiga yuborildi. User ID: {user_id}")
        except Exception as e:
            logging.error(f"HR guruhiga AppSheet muammosi yuborishda xatolik: {e}")
    
    # Foydalanuvchiga tasdiq xabari
    await message.answer(texts[lang]['appsheet_thanks'])
    
    # Asosiy menyuga qaytish
    if await db.is_admin(user_id):
        keyboard = get_admin_main_keyboard(lang)
    else:
        keyboard = get_employee_keyboard(lang)
    
    await message.answer(texts[lang]['welcome_menu'], reply_markup=keyboard)
    await state.set_state(MainForm.main_menu)


# --- HR GURUHIDA REPLY QILISH FUNKSIYASI ---

@router.message(F.reply_to_message)
async def handle_hr_group_reply(message: Message, bot: Bot):
    """HR guruhida bot xabariga reply qilinganda ishga tushadi (AppSheet muammolari uchun)"""
    
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
        logging.info(f"HR javobi foydalanuvchiga yuborildi (AppSheet muammosi). User ID: {user_id}, Reply: {message.text[:50]}")
        
    except Exception as e:
        logging.error(f"HR guruh javobini ishlashda xatolik (AppSheet muammosi): {e}")

