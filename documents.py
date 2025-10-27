# documents.py fayli (Hujjatlar bo'limi)

import os
import logging
from aiogram import Bot, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, FSInputFile
)

from states import MainForm, DocumentForm
from keyboards import texts, get_user_keyboard, get_admin_main_keyboard
import database as db

router = Router()

# Sozlamalar
ADMIN_ID = os.getenv("ADMIN_ID")


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
        # Agar tasdiqlangan xodim bo'lsa, kategoriyalarni ko'rsatamiz
        await show_categories(message, state)
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
    
    if str(message.from_user.id) == ADMIN_ID:
        keyboard = get_admin_main_keyboard(lang)
    else:
        keyboard = get_user_keyboard(lang)

    if is_authorized:
        logging.info(f"Xodim {user_phone_number} hujjatlar bo'limiga kirdi.")
        await message.answer(texts[lang]['documents_welcome'], reply_markup=ReplyKeyboardRemove())
        await show_categories(message, state)
    else:
        logging.warning(f"Ruxsatsiz urinish (xodim emas): {user_phone_number}")
        await message.answer(texts[lang]['documents_auth_fail'], reply_markup=keyboard)
        await state.set_state(MainForm.main_menu)


@router.message(DocumentForm.verification)
async def process_documents_verification_invalid(message: Message, state: FSMContext):
    """Noto'g'ri formatdagi xabar"""
    lang = await get_user_lang(state)
    await message.reply(texts[lang]['documents_auth_prompt'])


async def show_categories(message: Message | CallbackQuery, state: FSMContext):
    """Kategoriyalar menyusini ko'rsatish"""
    lang = await get_user_lang(state)
    
    # Kategoriyalar inline keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=texts[lang]['category_ariza'], callback_data="doc_category_ariza"),
        ],
        [
            InlineKeyboardButton(text=texts[lang]['category_kompaniya'], callback_data="doc_category_kompaniya"),
        ]
    ])
    
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(texts[lang]['documents_welcome'], reply_markup=keyboard)
    else:
        await message.answer(texts[lang]['documents_welcome'], reply_markup=keyboard)
    
    await state.set_state(DocumentForm.waiting_category)


@router.callback_query(DocumentForm.waiting_category, F.data.startswith('doc_category_'))
async def process_category_selection(callback: CallbackQuery, state: FSMContext):
    """Kategoriya tanlanganda"""
    category = callback.data.split('_')[2]  # ariza yoki kompaniya
    lang = await get_user_lang(state)
    
    # Kategoriyani state'ga saqlab qo'yamiz
    await state.update_data(document_category=category)
    
    # Kategoriya ichidagi hujjatlarni ko'rsatamiz
    documents = await db.get_documents_by_category(category, lang)
    
    if not documents:
        await callback.message.edit_text(
            f"❌ {texts[lang]['category_ariza'] if category == 'ariza' else texts[lang]['category_kompaniya']} bo'limida hujjat topilmadi.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=texts[lang]['back_to_categories'], callback_data="doc_back_categories")]
            ])
        )
        return
    
    # Hujjatlar ro'yxatini tugmalar ko'rinishida tayyorlaymiz
    keyboard_buttons = []
    for doc in documents:
        # Har bir hujjat uchun tugma
        keyboard_buttons.append([
            InlineKeyboardButton(text=doc['name'], callback_data=f"doc_select_{doc['id']}")
        ])
    
    # Orqaga tugmasi
    keyboard_buttons.append([
        InlineKeyboardButton(text=texts[lang]['back_to_categories'], callback_data="doc_back_categories")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    category_name = texts[lang]['category_ariza'] if category == 'ariza' else texts[lang]['category_kompaniya']
    await callback.message.edit_text(
        f"{category_name}\n\nKerakli hujjatni tanlang:",
        reply_markup=keyboard
    )
    await state.set_state(DocumentForm.waiting_document)
    await callback.answer()


@router.callback_query(DocumentForm.waiting_document, F.data.startswith('doc_select_'))
async def process_document_selection(callback: CallbackQuery, state: FSMContext):
    """Hujjat tanlanganda formatni so'rash"""
    doc_id = int(callback.data.split('_')[2])
    lang = await get_user_lang(state)
    
    # Hujjat ma'lumotlarini olamiz
    document = await db.get_document_by_id(doc_id)
    
    if not document:
        await callback.answer("Hujjat topilmadi.", show_alert=True)
        return
    
    # Hujjat ma'lumotlarini state'ga saqlaymiz
    await state.update_data(document_id=doc_id)
    
    # Format tanlash keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=texts[lang]['format_pdf'], callback_data=f"doc_format_{doc_id}_pdf"),
            InlineKeyboardButton(text=texts[lang]['format_docx'], callback_data=f"doc_format_{doc_id}_docx")
        ],
        [InlineKeyboardButton(text=texts[lang]['back_to_categories'], callback_data="doc_back_documents")]
    ])
    
    # Hujjat nomini lang bo'yicha tanlaymiz
    doc_name = document.name_uz if lang == 'uz' else document.name_ru
    
    await callback.message.edit_text(
        f"📄 {doc_name}\n\n{texts[lang]['choose_format']}",
        reply_markup=keyboard
    )
    await state.set_state(DocumentForm.waiting_format)
    await callback.answer()


@router.callback_query(DocumentForm.waiting_format, F.data.startswith('doc_format_'))
async def process_format_selection(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Format tanlanganda faylni yuborish"""
    lang = await get_user_lang(state)
    
    # Callback_data format: doc_format_{doc_id}_{format}
    parts = callback.data.split('_')
    doc_id = int(parts[2])
    format_type = parts[3]  # pdf yoki docx
    
    # Hujjat ma'lumotlarini olamiz
    document = await db.get_document_by_id(doc_id)
    
    if not document:
        await callback.answer("Hujjat topilmadi.", show_alert=True)
        return
    
    # Fayl yo'lini format va til bo'yicha tanlaymiz
    if format_type == 'pdf':
        file_path = document.file_path_uz_pdf if lang == 'uz' else document.file_path_ru_pdf
        file_name = f"{document.name_uz if lang == 'uz' else document.name_ru}.pdf"
    else:  # docx
        file_path = document.file_path_uz_docx if lang == 'uz' else document.file_path_ru_docx
        file_name = f"{document.name_uz if lang == 'uz' else document.name_ru}.docx"
    
    if not file_path:
        await callback.answer("Bu format mavjud emas.", show_alert=True)
        return
    
    # Faylni yuborish
    try:
        file = FSInputFile(file_path, filename=file_name)
        await bot.send_document(chat_id=callback.from_user.id, document=file)
        logging.info(f"Foydalanuvchi {callback.from_user.id} ga hujjat yuborildi: {file_name}")
        
        # Asosiy menyuga qaytish tugmasi
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=texts[lang]['back_to_categories'], callback_data="doc_back_categories")]
        ])
        await callback.message.edit_text(
            "✅ Hujjat yuborildi.",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logging.error(f"Faylni yuborishda xatolik: {e}")
        await callback.answer("Faylni yuborishda xatolik yuz berdi.", show_alert=True)
    
    await callback.answer()


@router.callback_query(F.data.in_(['doc_back_categories', 'doc_back_documents']))
async def process_back_button(callback: CallbackQuery, state: FSMContext):
    """Orqaga tugmasi bosilganda"""
    if callback.data == 'doc_back_categories':
        # Kategoriyalarga qaytish
        await show_categories(callback, state)
    else:
        # Kategoriya ichidagi hujjatlarga qaytish (fallback)
        await show_categories(callback, state)
    
    await callback.answer()

