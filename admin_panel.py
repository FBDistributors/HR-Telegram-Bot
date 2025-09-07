# admin_panel.py fayli (Iyerarxik bilimlar bazasi uchun yangilangan)

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


# --- Word faylni o'qish uchun YORDAMCHI FUNKSIYA (YANGILANDI) ---
def parse_docx(file_bytes: bytes) -> list:
    """
    Iyerarxik sarlavhalarga ega Word (.docx) faylini o'qiydi.
    Format:
    === Sarlavha 1-daraja ===
    == Sarlavha 2-daraja ==
    = Sarlavha 3-daraja =
    Izoh matni...
    """
    print("\n--- Iyerarxik faylni o'qish boshlandi ---")
    document = docx.Document(io.BytesIO(file_bytes))
    entries = []
    
    # Joriy sarlavhalar iyerarxiyasini saqlash uchun
    # path[0] -> 1-daraja, path[1] -> 2-daraja, path[2] -> 3-daraja
    current_path = [None, None, None]
    current_content = []
    
    def save_previous_entry():
        """Oldingi o'qilgan sarlavha va uning matnini saqlash uchun yordamchi funksiya."""
        if current_content and any(current_path):
            # None bo'lmagan sarlavhalarni " / " belgisi bilan birlashtiramiz
            full_topic = " / ".join(filter(None, [p.strip() if p else None for p in current_path]))
            
            if full_topic:
                entries.append({
                    'topic': full_topic,
                    'content': "\n".join(current_content).strip()
                })
                print(f"--> Saqlandi: Mavzu='{full_topic}'")

    for para in document.paragraphs:
        clean_text = para.text.strip()

        if not clean_text:
            continue

        # Sarlavhalarni darajasiga qarab tekshiramiz
        if clean_text.startswith('===') and clean_text.endswith('==='):
            save_previous_entry()
            current_content = []
            title = clean_text.replace('===', '').strip()
            current_path = [title, None, None] # 1-darajaga o'tamiz, quyi darajalarni tozalaymiz
            print(f"--> 1-daraja sarlavha: '{title}'")
            
        elif clean_text.startswith('==') and clean_text.endswith('=='):
            save_previous_entry()
            current_content = []
            title = clean_text.replace('==', '').strip()
            current_path[1] = title
            current_path[2] = None # Eng quyi darajani tozalaymiz
            print(f"--> 2-daraja sarlavha: '{title}'")

        elif clean_text.startswith('=') and clean_text.endswith('='):
            save_previous_entry()
            current_content = []
            title = clean_text.replace('=', '').strip()
            current_path[2] = title
            print(f"--> 3-daraja sarlavha: '{title}'")

        else:
            # Agar qator sarlavha bo'lmasa, uni matn (content) deb hisoblaymiz
            if any(current_path): # Faqat biror sarlavha ostida bo'lsagina qo'shamiz
                current_content.append(clean_text)

    # Sikl tugagandan so'ng eng oxirgi yozuvni saqlaymiz
    save_previous_entry()

    print(f"--- O'qish tugadi. Jami {len(entries)} ta yozuv topildi. ---")
    
    if not entries:
        raise ValueError("Faylda to'g'ri formatdagi sarlavhalar topilmadi (===, ==, =).")
        
    return entries


# --- BILIMLAR BAZASINI FAYL ORQALI YANGILASH ---

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
        # Xatolik matnini ham yangilaymiz
        error_text = texts[admin_lang]['kb_update_fail_parsing'].replace(
            "sarlavhalar `=== Sarlavha ===` ko'rinishida bo'lishi kerak",
            "sarlavhalar iyerarxiyasi (`===`, `==`, `=`) to'g'ri ekanligini tekshiring"
        )
        await callback.message.edit_text(error_text)
    
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
