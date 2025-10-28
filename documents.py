# documents.py fayli (Hujjatlar bo'limi - Yangilangan)

import os
import logging
from aiogram import Bot, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, FSInputFile
)
from sqlalchemy import select
from database import User, async_session_maker

from states import MainForm, DocumentForm
from keyboards import texts, get_user_keyboard, get_admin_main_keyboard
import database as db

router = Router()

# Sozlamalar


async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')


# --- HUJJATLAR BO'LIMI ---

@router.message(F.text.in_([texts['uz']['documents_button'], texts['ru']['documents_button']]))
async def handle_documents_button(message: Message, state: FSMContext):
    """Hujjatlar tugmasi bosilganda"""
    lang = await get_user_lang(state)
    user_id = message.from_user.id
    
    # Xodim ekanligini tekshirish
    if await db.is_employee_by_tg_id(user_id):
        # Agar tasdiqlangan xodim bo'lsa, bo'limlarni ko'rsatamiz
        await show_sections(message, state)
    else:
        # Agar tasdiqlanmagan bo'lsa, telefon raqam so'raymiz
        await handle_documents_verification(message, state)


async def handle_documents_verification(message: Message, state: FSMContext):
    """Xodim ekanligini tekshirish uchun telefon raqam so'rash"""
    lang = await get_user_lang(state)
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts[lang]['button_share_contact'], request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(texts[lang]['documents_auth_prompt'], reply_markup=contact_keyboard)
    await state.set_state(DocumentForm.verification)


@router.message(DocumentForm.verification, F.contact)
async def process_documents_verification(message: Message, state: FSMContext):
    """Telefon raqam orqali xodim ekanligini tekshirish"""
    lang = await get_user_lang(state)
    user_phone_number = message.contact.phone_number

    # Foydalanuvchini bazaga qo'shamiz (agar mavjud bo'lmasa)
    await db.add_user(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username
    )
    
    # Raqamni saqlaymiz
    await db.update_user_phone_number(message.from_user.id, user_phone_number)

    # Xodim ekanligini tekshiramiz
    is_authorized = await db.verify_employee_by_phone(user_phone_number, message.from_user.id)
    
    if await db.is_admin(message.from_user.id):
        keyboard = get_admin_main_keyboard(lang)
    else:
        keyboard = get_user_keyboard(lang)

    if is_authorized:
        logging.info(f"Xodim {user_phone_number} hujjatlar bo'limiga kirdi.")
        await message.answer(texts[lang]['documents_welcome'], reply_markup=ReplyKeyboardRemove())
        await show_sections(message, state)
    else:
        logging.warning(f"Ruxsatsiz urinish (xodim emas): {user_phone_number}")
        await message.answer(texts[lang]['documents_auth_fail'], reply_markup=keyboard)
        await state.set_state(MainForm.main_menu)


@router.message(DocumentForm.verification)
async def process_documents_verification_invalid(message: Message, state: FSMContext):
    """Noto'g'ri formatdagi xabar"""
    lang = await get_user_lang(state)
    await message.reply(texts[lang]['documents_auth_prompt'])


async def show_sections(message: Message | CallbackQuery, state: FSMContext):
    """2 bo'limni ko'rsatish: Namuna va Ma'lumot"""
    lang = await get_user_lang(state)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts[lang]['section_templates'], callback_data="doc_section_templates")],
        [InlineKeyboardButton(text=texts[lang]['section_info'], callback_data="doc_section_info")]
    ])
    
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(texts[lang]['documents_sections'], reply_markup=keyboard)
    else:
        await message.answer(texts[lang]['documents_sections'], reply_markup=keyboard)
    
    await state.set_state(DocumentForm.waiting_section)


# --- NAMUNA HUJJATLAR ---

@router.callback_query(DocumentForm.waiting_section, F.data == "doc_section_templates")
async def show_template_documents(callback: CallbackQuery, state: FSMContext):
    """Namuna hujjatlarni ko'rsatish"""
    lang = await get_user_lang(state)
    
    documents = await db.get_template_documents(lang)
    
    if not documents:
        await callback.message.edit_text(
            "❌ Hozircha namuna hujjatlar mavjud emas.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=texts[lang]['back_to_sections'], callback_data="doc_back_sections")]
            ])
        )
        return
    
    # Hujjatlar ro'yxatini tugmalar ko'rinishida tayyorlaymiz
    keyboard_buttons = []
    for doc in documents:
        keyboard_buttons.append([
            InlineKeyboardButton(text=doc['name'], callback_data=f"doc_template_{doc['id']}")
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text=texts[lang]['back_to_sections'], callback_data="doc_back_sections")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text(
        "📝 Namuna hujjatlar:\n\nKerakli hujjatni tanlang:",
        reply_markup=keyboard
    )
    await state.set_state(DocumentForm.waiting_template_document)
    await callback.answer()


@router.callback_query(DocumentForm.waiting_template_document, F.data.startswith('doc_template_'))
async def select_template_language(callback: CallbackQuery, state: FSMContext):
    """Namuna hujjat tanlanganda tilni so'rash"""
    doc_id = int(callback.data.split('_')[2])
    lang = await get_user_lang(state)
    
    await state.update_data(template_doc_id=doc_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data=f"doc_lang_{doc_id}_uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data=f"doc_lang_{doc_id}_ru")],
        [InlineKeyboardButton(text=texts[lang]['back_to_sections'], callback_data="doc_back_sections")]
    ])
    
    doc = await db.get_document_by_id(doc_id)
    doc_name = doc.name_uz if lang == 'uz' else doc.name_ru
    
    await callback.message.edit_text(
        f"📄 {doc_name}\n\n{texts[lang]['select_language']}",
        reply_markup=keyboard
    )
    await state.set_state(DocumentForm.waiting_language)
    await callback.answer()


@router.callback_query(DocumentForm.waiting_language, F.data.startswith('doc_lang_'))
async def select_template_format(callback: CallbackQuery, state: FSMContext):
    """Til tanlanganda formatni so'rash"""
    parts = callback.data.split('_')
    doc_id = int(parts[2])
    selected_lang = parts[3]
    
    lang = await get_user_lang(state)
    
    await state.update_data(template_lang=selected_lang)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts[lang]['format_pdf'], callback_data=f"doc_format_{doc_id}_pdf")],
        [InlineKeyboardButton(text=texts[lang]['format_docx'], callback_data=f"doc_format_{doc_id}_docx")],
        [InlineKeyboardButton(text=texts[lang]['back_to_sections'], callback_data="doc_back_sections")]
    ])
    
    await callback.message.edit_text(
        f"📄 {texts[lang]['choose_format']}",
        reply_markup=keyboard
    )
    await state.set_state(DocumentForm.waiting_format)
    await callback.answer()


@router.callback_query(DocumentForm.waiting_format, F.data.startswith('doc_format_'))
async def send_template_file(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Format tanlanganda faylni yuborish (Namuna hujjatlar)"""
    lang = await get_user_lang(state)
    
    parts = callback.data.split('_')
    doc_id = int(parts[2])
    format_type = parts[3]
    
    user_data = await state.get_data()
    selected_lang = user_data.get('template_lang', lang)
    
    document = await db.get_document_by_id(doc_id)
    
    if not document:
        await callback.answer("Hujjat topilmadi.", show_alert=True)
        return
    
    # Fayl yo'lini format va tanlangan til bo'yicha tanlaymiz
    if format_type == 'pdf':
        file_path = document.file_path_uz_pdf if selected_lang == 'uz' else document.file_path_ru_pdf
        file_name = f"{document.name_uz if selected_lang == 'uz' else document.name_ru}.pdf"
    else:  # docx
        file_path = document.file_path_uz_docx if selected_lang == 'uz' else document.file_path_ru_docx
        file_name = f"{document.name_uz if selected_lang == 'uz' else document.name_ru}.docx"
    
    if not file_path:
        await callback.answer("Bu format mavjud emas.", show_alert=True)
        return
    
    # Faylni yuborish
    try:
        file = FSInputFile(file_path, filename=file_name)
        await bot.send_document(chat_id=callback.from_user.id, document=file)
        logging.info(f"Namuna hujjat yuborildi: {file_name}")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=texts[lang]['back_to_sections'], callback_data="doc_back_sections")]
        ])
        await callback.message.edit_text("✅ Hujjat yuborildi.", reply_markup=keyboard)
        
    except Exception as e:
        logging.error(f"Faylni yuborishda xatolik: {e}")
        await callback.answer("Faylni yuborishda xatolik.", show_alert=True)
    
    await callback.answer()


# --- MA'LUMOT HUJJATLARI ---

@router.callback_query(DocumentForm.waiting_section, F.data == "doc_section_info")
async def show_info_documents(callback: CallbackQuery, state: FSMContext):
    """Ma'lumot hujjatlarni ko'rsatish"""
    lang = await get_user_lang(state)
    
    documents = await db.get_info_documents(lang)
    
    if not documents:
        await callback.message.edit_text(
            "❌ Hozircha ma'lumot hujjatlari mavjud emas.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=texts[lang]['back_to_sections'], callback_data="doc_back_sections")]
            ])
        )
        return
    
    # Hujjatlar ro'yxatini tugmalar ko'rinishida tayyorlaymiz
    keyboard_buttons = []
    for doc in documents:
        # Ma'lumotlarni formatlaymiz
        doc_info = doc['name']
        if doc.get('document_type'):
            type_emoji = {
                'Hisobot': '📊',
                'Ariza': '📝',
                'Ko\'rsatma': '📋',
                'Umumiy': '📁'
            }.get(doc['document_type'], '📄')
            doc_info = f"{type_emoji} {doc['name']}"
        
        keyboard_buttons.append([
            InlineKeyboardButton(text=doc_info, callback_data=f"doc_info_{doc['id']}")
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text=texts[lang]['back_to_sections'], callback_data="doc_back_sections")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text(
        "📄 Ma'lumot hujjatlari:\n\nKerakli hujjatni tanlang:",
        reply_markup=keyboard
    )
    await state.set_state(DocumentForm.waiting_info_document)
    await callback.answer()


@router.callback_query(DocumentForm.waiting_info_document, F.data.startswith('doc_info_'))
async def send_info_file(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Ma'lumot hujjat tanlanganda to'g'ridan-to'g'ri yuborish"""
    lang = await get_user_lang(state)
    
    doc_id = int(callback.data.split('_')[2])
    
    documents = await db.get_info_documents(lang)
    doc = None
    for d in documents:
        if d['id'] == doc_id:
            doc = d
            break
    
    if not doc or not doc.get('file_path'):
        await callback.answer("Hujjat topilmadi.", show_alert=True)
        return
    
    # Faylni yuborish
    try:
        # Fayl nomini formatalash
        file_name = os.path.basename(doc['file_path'])
        file = FSInputFile(doc['file_path'], filename=file_name)
        await bot.send_document(chat_id=callback.from_user.id, document=file)
        
        # Qo'shimcha ma'lumot (agar mavjud bo'lsa)
        info_text = f"📄 {doc['name']}"
        
        # Kim yuklagan va qachon
        if doc.get('uploaded_by'):
            async with async_session_maker() as session:
                result = await session.execute(select(User).filter(User.user_id == doc['uploaded_by']))
                user = result.scalars().first()
                if user:
                    info_text += f"\n{texts[lang]['uploaded_by'].format(name=user.full_name)}"
        
        if doc.get('created_at'):
            info_text += f"\n{texts[lang]['uploaded_at'].format(date=doc['created_at'])}"
        
        if doc.get('document_type'):
            info_text += f"\n{texts[lang]['doc_type'].format(type=doc['document_type'])}"
        
        await bot.send_message(chat_id=callback.from_user.id, text=info_text)
        
        logging.info(f"Ma'lumot hujjati yuborildi: {file_name}")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=texts[lang]['back_to_sections'], callback_data="doc_back_sections")]
        ])
        await callback.message.edit_text("✅ Hujjat yuborildi.", reply_markup=keyboard)
        
    except Exception as e:
        logging.error(f"Faylni yuborishda xatolik: {e}")
        await callback.answer("Faylni yuborishda xatolik.", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data == "doc_back_sections")
async def process_back_to_sections(callback: CallbackQuery, state: FSMContext):
    """Bo'limlarga qaytish"""
    await show_sections(callback, state)
    await callback.answer()
