# admin_panel.py fayli (Diagnostika uchun maxsus versiya)

import os
import logging
import io
import docx
from aiogram import Bot, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
)

import database as db
from keyboards import texts, get_admin_main_keyboard
from states import AdminForm, MainForm, KnowledgeBaseAdmin

router = Router()
ADMIN_ID = os.getenv("ADMIN_ID")

async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')


# --- Word faylni o'qish uchun yordamchi funksiya (DIAGNOSTIKA BILAN) ---
def parse_docx(file_bytes: bytes) -> list:
    """
    Word (.docx) faylini o'qiydi va har bir qatorni terminalga chiqaradi.
    """
    print("\n--- Faylni o'qish boshlandi ---")
    document = docx.Document(io.BytesIO(file_bytes))
    entries = []
    current_topic = None
    current_content = []
    line_number = 0

    for para in document.paragraphs:
        line_number += 1
        clean_text = para.text.strip()
        
        # Har bir qatorni terminalga chiqaramiz
        print(f"Qator {line_number}: '{clean_text}'")

        if not clean_text:
            print("--> Bo'sh qator, o'tkazib yuborildi.")
            continue

        if clean_text.startswith('===') and clean_text.endswith('==='):
            print(f"--> SARLAVHA TOPILDI: '{clean_text}'")
            if current_topic and current_content:
                entries.append({'topic': current_topic, 'content': "\n".join(current_content)})
            
            current_topic = clean_text.replace('===', '').strip()
            current_content = []
            print(f"--> Yangi mavzu: '{current_topic}'")
        elif current_topic:
            print("--> Mavzu matniga qo'shildi.")
            current_content.append(clean_text)
        else:
            print("--> E'tiborsiz qoldirildi (hali birorta sarlavha topilmadi).")


    if current_topic and current_content:
        entries.append({'topic': current_topic, 'content': "\n".join(current_content)})

    print(f"--- O'qish tugadi. Topilgan mavzular soni: {len(entries)} ---")
    
    if not entries:
        raise ValueError("Faylda to'g'ri formatdagi sarlavhalar topilmadi.")
        
    return entries


# --- BILIMLAR BAZASINI FAYL ORQALI YANGILASH ---
# (Bu yerdan boshlab qolgan kod o'zgarishsiz qoladi)

@router.message(F.text.in_([texts['uz']['kb_update_button'], texts['ru']['kb_update_button']]))
async def handle_kb_update_button(message: Message, state: FSMContext):
    lang = await get_user_lang(state)
    await message.answer(texts[lang]['ask_for_kb_file'], reply_markup=ReplyKeyboardRemove())
    await state.set_state(KnowledgeBaseAdmin.waiting_for_kb_file)


@router.message(KnowledgeBaseAdmin.waiting_for_kb_file, F.document)
async def handle_kb_file(message: Message, state: FSMContext, bot: Bot):
    lang = await get_user_lang(state)
    
    if not message.document or not message.document.file_name.endswith('.docx'):
        await message.reply(texts[lang]['kb_update_fail_format'])
        return

    file_id = message.document.file_id
    file_info = await bot.get_file(file_id)
    file_bytes_io = await bot.download_file(file_info.file_path)

    await state.update_data(kb_file_bytes=file_bytes_io.read())

    lang_choice_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="kb_lang_uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="kb_lang_ru")]
    ])

    await message.answer(texts[lang]['kb_file_received'], reply_markup=lang_choice_kb)
    await state.set_state(KnowledgeBaseAdmin.waiting_for_lang_choice)


@router.callback_query(KnowledgeBaseAdmin.waiting_for_lang_choice, F.data.startswith('kb_lang_'))
async def process_kb_lang_choice(callback: CallbackQuery, state: FSMContext):
    chosen_lang = callback.data.split('_')[2]
    admin_lang = await get_user_lang(state)
    
    await callback.message.edit_text("⏳ Baza yangilanmoqda, iltimos kuting...")

    user_data = await state.get_data()
    file_bytes = user_data.get('kb_file_bytes')
    
    if not file_bytes:
        await callback.message.answer("❌ Xatolik: Fayl topilmadi. Qaytadan urinib ko'ring.")
        await state.set_state(MainForm.main_menu)
        return

    try:
        parsed_entries = parse_docx(file_bytes)
        await db.replace_kb_from_list(parsed_entries, chosen_lang)
        await callback.message.edit_text(texts[admin_lang]['kb_update_success'])
    except Exception as e:
        logging.error(f"Faylni qayta ishlashda xatolik: {e}")
        await callback.message.edit_text(texts[admin_lang]['kb_update_fail_parsing'])
    
    await state.set_state(MainForm.main_menu)
    await callback.answer()


# --- E'LON YUBORISH BO'LIMI ---

@router.message(F.text.in_([texts['uz']['broadcast_button'], texts['ru']['broadcast_button']]))
async def handle_broadcast_button(message: Message, state: FSMContext):
    if str(message.from_user.id) == ADMIN_ID:
        lang = await get_user_lang(state)
        await message.answer(texts[lang]['ask_announcement'], reply_markup=ReplyKeyboardRemove())
        await state.set_state(AdminForm.waiting_for_announcement)

@router.message(AdminForm.waiting_for_announcement, F.text)
async def send_announcement_to_all(message: Message, state: FSMContext, bot: Bot):
    lang = await get_user_lang(state)
    await message.answer(texts[lang]['broadcast_started'])
    
    announcement_text = message.text
    all_user_ids = await db.get_all_user_ids()

    success_count = 0
    fail_count = 0

    for user_id in all_user_ids:
        try:
            await bot.send_message(chat_id=user_id, text=announcement_text)
            success_count += 1
        except Exception as e:
            logging.warning(f"Foydanuvchi {user_id} ga xabar yuborib bo'lmadi: {e}")
            fail_count += 1

    report_text = texts[lang]['broadcast_report'].format(
        success_count=success_count, 
        fail_count=fail_count
    )
    await message.answer(
        report_text,
        reply_markup=get_admin_main_keyboard(lang)
    )
    await state.set_state(MainForm.main_menu)

