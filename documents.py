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
    user_id = message.from_user.id
    
    # Xodim ekanligini tekshirish
    if await db.is_employee_by_tg_id(user_id):
        # To'g'ridan-to'g'ri kategoriyalarni ko'rsatamiz
        await show_template_categories(message, state)
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

    try:
        # Telefon raqam formatini tekshirish
        if not user_phone_number or len(user_phone_number.replace('+', '').replace(' ', '').replace('-', '')) < 7:
            await message.answer("❌ Telefon raqam noto'g'ri formatda. Iltimos, qaytadan urinib ko'ring.", 
                               reply_markup=get_user_keyboard(lang))
            await state.set_state(MainForm.main_menu)
            return

        # Foydalanuvchini bazaga qo'shamiz (telefon raqami bilan)
        await db.add_user(
            user_id=message.from_user.id,
            full_name=message.from_user.full_name,
            username=message.from_user.username,
            phone_number=user_phone_number
        )

        # Xodim ekanligini tekshiramiz
        is_authorized = await db.verify_employee_by_phone(user_phone_number, message.from_user.id)
        
        if await db.is_admin(message.from_user.id):
            keyboard = get_admin_main_keyboard(lang)
        else:
            keyboard = get_user_keyboard(lang)

        if is_authorized:
            logging.info(f"Xodim {user_phone_number} hujjatlar bo'limiga kirdi.")
            await message.answer(texts[lang]['documents_welcome'], reply_markup=ReplyKeyboardRemove())
            await show_template_categories(message, state)
        else:
            logging.warning(f"Ruxsatsiz urinish (xodim emas): {user_phone_number}")
            await message.answer(texts[lang]['documents_auth_fail'], reply_markup=keyboard)
            await state.set_state(MainForm.main_menu)
            
    except Exception as e:
        logging.error(f"Documents verification xatoligi: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.", 
                           reply_markup=get_user_keyboard(lang))
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
async def show_template_categories_callback(callback: CallbackQuery, state: FSMContext):
    await show_template_categories(callback, state)


async def show_template_categories(message_or_cb: Message | CallbackQuery, state: FSMContext):
    """Namuna hujjatlar uchun kategoriyalarni ko'rsatish (Message yoki Callback)."""
    lang = await get_user_lang(state)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts[lang]['tmpl_cat_entry_form'], callback_data='tmpl_cat_entry')],
        [InlineKeyboardButton(text=texts[lang]['tmpl_cat_dismissal'], callback_data='tmpl_cat_dismissal')],
        [InlineKeyboardButton(text=texts[lang]['tmpl_cat_exit_interview'], callback_data='tmpl_cat_exit')],
        [InlineKeyboardButton(text=texts[lang]['tmpl_cat_vacation'], callback_data='tmpl_cat_vacation')],
        [InlineKeyboardButton(text=texts[lang]['tmpl_cat_leave_without_pay'], callback_data='tmpl_cat_leave_without_pay')],
        [InlineKeyboardButton(text=texts[lang]['info_category_debt'], callback_data='tmpl_cat_debt')],
    ])

    if isinstance(message_or_cb, CallbackQuery):
        await message_or_cb.message.edit_text(texts[lang]['template_categories_title'], reply_markup=keyboard)
        await message_or_cb.answer()
    else:
        await message_or_cb.answer(texts[lang]['template_categories_title'], reply_markup=keyboard)
    await state.set_state(DocumentForm.waiting_template_category)


@router.callback_query(DocumentForm.waiting_template_category, F.data.startswith('tmpl_cat_'))
async def send_template_by_category(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Kategoriya tugmasi bosilganda, shu kategoriya uchun birinchi mavjud PDFni darhol yuborish."""
    lang = await get_user_lang(state)

    cb = callback.data
    if cb == 'tmpl_cat_debt':
        # Qarzdorlik: info hujjat, Excel bo'lishi mumkin. Birinchi mavjud faylni yuboramiz.
        documents = await db.get_debt_documents()
        if not documents:
            await callback.message.edit_text(
                texts[lang]['no_debt_documents'],
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=texts[lang]['back_to_template_categories'], callback_data='doc_back_template_categories')]
                ])
            )
            await callback.answer()
            return
        doc = documents[0]
        try:
            if not doc.file_path_single or not os.path.exists(doc.file_path_single):
                await callback.answer("Fayl topilmadi.", show_alert=True)
                return
            file = FSInputFile(doc.file_path_single)
            doc_name = doc.name_uz if lang == 'uz' else (doc.name_ru or doc.name_uz)
            await callback.message.answer_document(file, caption=f"💰 {doc_name}")

            # Qo'shimcha ma'lumot: kim yuklagan va sana (faqat Qarzdorlik uchun)
            info_text = f"📄 {doc_name}"
            if doc.uploaded_by:
                async with async_session_maker() as session:
                    result = await session.execute(select(User).filter(User.user_id == doc.uploaded_by))
                    user = result.scalars().first()
                    if user:
                        info_text += f"\n{texts[lang]['uploaded_by'].format(name=user.full_name)}"
            if doc.created_at:
                info_text += f"\n{texts[lang]['uploaded_at'].format(date=doc.created_at)}"
            await bot.send_message(chat_id=callback.from_user.id, text=info_text)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=texts[lang]['back_to_template_categories'], callback_data='doc_back_template_categories')]
            ])
            await callback.message.edit_text("✅ Hujjat yuborildi.", reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Qarzdorlik faylini yuborishda xato: {e}")
            await callback.answer("Faylni yuborishda xatolik.", show_alert=True)
    else:
        # Template kategoriyalari
        if cb == 'tmpl_cat_entry':
            db_category = "Ishga kirish anketasi"
        elif cb == 'tmpl_cat_dismissal':
            db_category = "Bo'shatish"
        elif cb == 'tmpl_cat_exit':
            db_category = "Ishdan bo'shash oldidan intervyu"
        elif cb == 'tmpl_cat_vacation':
            db_category = "Ta'til uchun ariza"
        elif cb == 'tmpl_cat_leave_without_pay':
            db_category = "O'z hisobidan ta'til"
        else:
            await callback.answer("Noma'lum kategoriya.", show_alert=True)
            return

        docs = await db.get_template_documents_by_category(db_category, lang)

        if not docs:
            await callback.message.edit_text(
                texts[lang]['no_templates_in_category'],
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=texts[lang]['back_to_template_categories'], callback_data='doc_back_template_categories')],
                ])
            )
            await state.set_state(DocumentForm.waiting_template_category)
            await callback.answer()
            return

        chosen = docs[0]
        full_doc = await db.get_document_by_id(chosen['id'])
        if not full_doc:
            await callback.answer("Hujjat topilmadi.", show_alert=True)
            return

        file_path = full_doc.file_path_uz_pdf or full_doc.file_path_ru_pdf or full_doc.file_path_single
        doc_name = full_doc.name_uz if lang == 'uz' else (full_doc.name_ru or full_doc.name_uz)

        if not file_path:
            await callback.answer("PDF fayl mavjud emas.", show_alert=True)
            return

        try:
            file = FSInputFile(file_path, filename=f"{doc_name}.pdf")
            await bot.send_document(chat_id=callback.from_user.id, document=file)

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=texts[lang]['back_to_template_categories'], callback_data='doc_back_template_categories')]
            ])
            await callback.message.edit_text("✅ Hujjat yuborildi.", reply_markup=keyboard)
        except Exception as e:
            logging.error(f"Kategoriya bo'yicha fayl yuborishda xatolik: {e}")
            await callback.answer("Faylni yuborishda xatolik.", show_alert=True)

    await callback.answer()


@router.callback_query(F.data == 'doc_back_template_categories')
async def back_to_template_categories(callback: CallbackQuery, state: FSMContext):
    """Hujjatlar ro'yxatidan kategoriyalar menyusiga qaytish"""
    await show_template_categories(callback, state)
    await callback.answer()


@router.callback_query(DocumentForm.waiting_template_document, F.data.startswith('doc_template_'))
async def send_template_pdf(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Namuna hujjat tanlanganda darhol PDF yuboriladi (til/format so'ralmaydi)."""
    lang = await get_user_lang(state)
    doc_id = int(callback.data.split('_')[2])

    document = await db.get_document_by_id(doc_id)
    if not document:
        await callback.answer("Hujjat topilmadi.", show_alert=True)
        return

    # PDF faylini tanlash: mavjudlar ichidan birinchi
    file_path = document.file_path_uz_pdf or document.file_path_ru_pdf or document.file_path_single
    doc_name = document.name_uz if lang == 'uz' else (document.name_ru or document.name_uz)

    if not file_path:
        await callback.answer("PDF fayl mavjud emas.", show_alert=True)
        return

    try:
        file = FSInputFile(file_path, filename=f"{doc_name}.pdf")
        await bot.send_document(chat_id=callback.from_user.id, document=file)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=texts[lang]['back_to_template_categories'], callback_data='doc_back_template_categories')],
            [InlineKeyboardButton(text=texts[lang]['back_to_sections'], callback_data='doc_back_sections')]
        ])
        await callback.message.edit_text("✅ Hujjat yuborildi.", reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Faylni yuborishda xatolik: {e}")
        await callback.answer("Faylni yuborishda xatolik.", show_alert=True)

    await callback.answer()


## Til va format bosqichlari olib tashlandi (PDF bevosita yuboriladi)


## Eski format handleri olib tashlandi (oqim soddalashtirildi)


# --- MA'LUMOT HUJJATLARI ---

@router.callback_query(DocumentForm.waiting_section, F.data == "doc_section_info")
async def show_info_categories(callback: CallbackQuery, state: FSMContext):
    """Ma'lumot hujjatlari kategoriyalarini ko'rsatish"""
    lang = await get_user_lang(state)
    
    # Hozircha faqat Qarzdorlik kategoriyasi mavjud
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts[lang]['info_category_debt'], callback_data="info_cat_debt")],
        [InlineKeyboardButton(text=texts[lang]['back_to_sections'], callback_data="doc_back_sections")]
    ])
    
    await callback.message.edit_text(
        texts[lang]['documents_sections'],
        reply_markup=keyboard
    )
    await state.set_state(DocumentForm.waiting_info_category)
    await callback.answer()


@router.callback_query(DocumentForm.waiting_info_category, F.data == "info_cat_debt")
async def show_debt_documents(callback: CallbackQuery, state: FSMContext):
    """Qarzdorlik hujjatlarini ko'rsatish"""
    lang = await get_user_lang(state)
    
    documents = await db.get_debt_documents()
    
    if not documents:
        await callback.message.edit_text(
            texts[lang]['no_debt_documents'],
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=texts[lang]['back_to_sections'], callback_data="doc_back_sections")]
            ])
        )
        await callback.answer()
        return
    
    # Qarzdorlik hujjatlari ro'yxatini tugmalar ko'rinishida tayyorlaymiz
    keyboard_buttons = []
    for doc in documents:
        # Hujjat nomini formatlash
        doc_info = f"💰 {doc.name_uz if lang == 'uz' else doc.name_ru or doc.name_uz}"
        
        keyboard_buttons.append([
            InlineKeyboardButton(text=doc_info, callback_data=f"debt_doc_{doc.id}")
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text=texts[lang]['back_to_sections'], callback_data="doc_back_sections")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text(
        texts[lang]['debt_documents'],
        reply_markup=keyboard
    )
    await state.set_state(DocumentForm.waiting_debt_document)
    await callback.answer()


@router.callback_query(DocumentForm.waiting_debt_document, F.data.startswith('debt_doc_'))
async def send_debt_file(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Qarzdorlik hujjat tanlanganda to'g'ridan-to'g'ri yuborish"""
    lang = await get_user_lang(state)
    
    doc_id = int(callback.data.split('_')[2])
    
    documents = await db.get_debt_documents()
    doc = None
    for d in documents:
        if d.id == doc_id:
            doc = d
            break
    
    if not doc or not doc.file_path_single:
        await callback.answer("Hujjat topilmadi.", show_alert=True)
        return
    
    # Faylni yuborish
    try:
        file_path = doc.file_path_single
        if not os.path.exists(file_path):
            await callback.answer("Fayl topilmadi.", show_alert=True)
            return
        
        file = FSInputFile(file_path)
        doc_name = doc.name_uz if lang == 'uz' else doc.name_ru or doc.name_uz
        
        # Hujjatni yuborish
        await callback.message.answer_document(
            file,
            caption=f"💰 {doc_name}",
        )
        
        # Qo'shimcha ma'lumot (kim yuklagan va qachon)
        info_text = f"📄 {doc_name}"
        
        # Kim yuklagan va qachon
        if doc.uploaded_by:
            async with async_session_maker() as session:
                result = await session.execute(select(User).filter(User.user_id == doc.uploaded_by))
                user = result.scalars().first()
                if user:
                    info_text += f"\n{texts[lang]['uploaded_by'].format(name=user.full_name)}"
        
        if doc.created_at:
            info_text += f"\n{texts[lang]['uploaded_at'].format(date=doc.created_at)}"
        
        await bot.send_message(
            chat_id=callback.from_user.id, 
            text=info_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=texts[lang]['back_to_sections'], callback_data="doc_back_sections")]
            ])
        )
        
        await callback.message.delete()
        await state.set_state(DocumentForm.waiting_section)
        
    except Exception as e:
        logging.error(f"Qarzdorlik hujjat yuborishda xatolik: {e}")
        await callback.answer("Faylni yuborishda xatolik yuz berdi.", show_alert=True)


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
