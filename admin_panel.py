# admin_panel.py fayli (Iyerarxik bilimlar bazasi uchun yangilangan)

import os
from datetime import datetime
import logging
import io
import docx
import aiofiles
from aiogram import Bot, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, FSInputFile
)

import database as db
from keyboards import texts, get_admin_main_keyboard
from states import AdminForm, MainForm, KnowledgeBaseAdmin, AddDocumentForm

router = Router()

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


## Removed adddoc_lang flow as per user request (directly show doc type)

# --- E'LON YUBORISH BO'LIMI ---

@router.message(F.text.in_([texts['uz']['broadcast_button'], texts['ru']['broadcast_button']]))
async def handle_broadcast_button(message: Message, state: FSMContext):
    if await db.is_admin(message.from_user.id):
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


# --- HUJJAT QO'SHISH BO'LIMI ---

@router.message(F.text.in_([texts['uz']['add_document_button'], texts['ru']['add_document_button']]))
async def handle_add_document_button(message: Message, state: FSMContext):
    """Hujjat qo'shish tugmasi bosilganda"""
    if await db.is_admin(message.from_user.id):
        lang = await get_user_lang(state)
        # To'g'ridan-to'g'ri kategoriya tugmalarini ko'rsatamiz (doc type yo'q)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=texts[lang]['tmpl_cat_entry_form'], callback_data='add_tmpl_cat_entry')],
            [InlineKeyboardButton(text=texts[lang]['tmpl_cat_dismissal'], callback_data='add_tmpl_cat_dismissal')],
            [InlineKeyboardButton(text=texts[lang]['tmpl_cat_exit_interview'], callback_data='add_tmpl_cat_exit')],
            [InlineKeyboardButton(text=texts[lang]['tmpl_cat_vacation'], callback_data='add_tmpl_cat_vacation')],
            [InlineKeyboardButton(text=texts[lang]['tmpl_cat_leave_without_pay'], callback_data='add_tmpl_cat_leave_without_pay')],
            [InlineKeyboardButton(text=texts[lang]['info_category_debt'], callback_data='add_info_debt')],
        ])
        await message.answer(texts[lang]['ask_template_category'], reply_markup=keyboard)
        await state.set_state(AddDocumentForm.waiting_template_category)


@router.callback_query(AddDocumentForm.waiting_doc_type)
async def process_doc_type_choice(callback: CallbackQuery, state: FSMContext):
    """Hujjat turi tanlandi"""
    lang = await get_user_lang(state)
    doc_type = callback.data.split('_')[2]  # template yoki info
    
    await state.update_data(doc_type=doc_type)
    
    if doc_type == 'template':
        # Avval kategoriya tanlanadi
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=texts[lang]['tmpl_cat_entry_form'], callback_data='add_tmpl_cat_entry')],
            [InlineKeyboardButton(text=texts[lang]['tmpl_cat_dismissal'], callback_data='add_tmpl_cat_dismissal')],
            [InlineKeyboardButton(text=texts[lang]['tmpl_cat_exit_interview'], callback_data='add_tmpl_cat_exit')],
        ])
        await callback.message.edit_text(texts[lang]['ask_template_category'], reply_markup=keyboard)
        await state.set_state(AddDocumentForm.waiting_template_category)
    else:  # info
        # Ma'lumot hujjat uchun avval kategoriya tanlash
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=texts[lang]['info_category_debt'], callback_data="info_category_debt")],
        ])
        await callback.message.edit_text(texts[lang]['ask_info_category'], reply_markup=keyboard)
        await state.set_state(AddDocumentForm.waiting_info_category)
    
    await callback.answer()


@router.callback_query(AddDocumentForm.waiting_template_category)
async def process_template_category_choice(callback: CallbackQuery, state: FSMContext):
    """Namuna hujjat uchun kategoriya tanlash"""
    lang = await get_user_lang(state)

    is_info = False
    if callback.data == 'add_tmpl_cat_entry':
        category = "Ishga kirish anketasi"
    elif callback.data == 'add_tmpl_cat_dismissal':
        category = "Bo'shatish"
    elif callback.data == 'add_tmpl_cat_exit':
        category = "Ishdan bo'shash oldidan intervyu"
    elif callback.data == 'add_tmpl_cat_vacation':
        category = "Ta'til uchun ariza"
    elif callback.data == 'add_tmpl_cat_leave_without_pay':
        category = "O'z hisobidan ta'til"
    else:  # add_info_debt
        category = "Qarzdorlik"
        is_info = True

    await state.update_data(template_category=category, add_is_info=is_info)
    # Ism so'ramaymiz, darhol fayl so'raymiz (Debt uchun Excel, boshqalar uchun PDF)
    prompt_text = texts[lang]['ask_debt_excel'] if is_info else texts[lang]['ask_template_uz_pdf']
    await callback.message.edit_text(prompt_text)
    await state.set_state(AddDocumentForm.waiting_template_uz_pdf)
    await callback.answer()


@router.callback_query(AddDocumentForm.waiting_info_category)
async def process_info_category_choice(callback: CallbackQuery, state: FSMContext):
    """Ma'lumot hujjat kategoriyasi tanlandi"""
    lang = await get_user_lang(state)
    
    # Kategoriya ma'lumotini saqlash
    if callback.data == "info_category_debt":
        category = "Qarzdorlik"
    else:
        category = "Umumiy"  # Default
    
    await state.update_data(info_category=category)
    
    # Endi fayl yuklashga o'tish
    await callback.message.edit_text(texts[lang]['ask_info_file'])
    await state.set_state(AddDocumentForm.waiting_info_file)
    await callback.answer()


# --- NAMUNA HUJJAT QO'SHISH ---

@router.message(AddDocumentForm.waiting_template_name_uz, F.text)
async def process_template_name_uz(message: Message, state: FSMContext):
    """Namuna hujjat - o'zbekcha nom"""
    lang = await get_user_lang(state)
    await state.update_data(name_uz=message.text)
    await message.answer(texts[lang]['ask_template_name_ru'])
    await state.set_state(AddDocumentForm.waiting_template_name_ru)


@router.message(AddDocumentForm.waiting_template_name_ru, F.text)
async def process_template_name_ru(message: Message, state: FSMContext):
    """Namuna hujjat - ruscha nom"""
    lang = await get_user_lang(state)
    await state.update_data(name_ru=message.text)
    await message.answer(texts[lang]['ask_template_uz_pdf'])
    await state.set_state(AddDocumentForm.waiting_template_uz_pdf)


@router.message(AddDocumentForm.waiting_template_uz_pdf, F.document)
async def process_template_uz_pdf(message: Message, state: FSMContext, bot: Bot):
    """Namuna hujjat - o'zbekcha PDF"""
    lang = await get_user_lang(state)
    
    if not message.document:
        await message.answer(texts[lang]['doc_add_error'])
        return
    
    # Faylni saqlash
    file_id = message.document.file_id
    file_info = await bot.get_file(file_id)
    file_bytes_io = await bot.download_file(file_info.file_path)
    
    # Faylni diskga saqlash
    import os
    # Info yoki Template ekanligini holatdan olamiz
    user_data_before = await state.get_data()
    is_info_add = user_data_before.get('add_is_info') is True

    target_dir = 'documents/info' if is_info_add else 'documents/templates'
    os.makedirs(target_dir, exist_ok=True)
    # Fayl nomini noyob qilish uchun timestamp qo'shamiz
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_name = message.document.file_name
    file_path = f"{target_dir}/{timestamp}_{safe_name}"
    file_content = file_bytes_io.read()
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_content)
    
    # Nomni fayl nomidan olish (agar hali belgilanmagan bo'lsa)
    try:
        base_name = os.path.splitext(message.document.file_name)[0]
    except Exception:
        base_name = None
    if base_name:
        user_data_current = await state.get_data()
        if not user_data_current.get('name_uz'):
            await state.update_data(name_uz=base_name)

    await state.update_data(file_path_uz_pdf=file_path)

    # Endi faqat bitta fayl talab qilinadi: shu yerning o'zida saqlab yakunlaymiz
    user_data = await state.get_data()

    # Nomlarni to'ldirish: agar mavjud bo'lmasa, fayl nomidan
    base_name = None
    try:
        base_name = os.path.splitext(message.document.file_name)[0]
    except Exception:
        pass
    name_uz = user_data.get('name_uz') or base_name or 'Hujjat'
    name_ru = user_data.get('name_ru') or name_uz

    try:
        if is_info_add:
            # Excel formatini tekshiramiz (.xlsx yoki .xls)
            if not (safe_name.lower().endswith('.xlsx') or safe_name.lower().endswith('.xls')):
                await message.answer("❌ Iltimos, faqat Excel fayl yuboring (.xlsx yoki .xls).")
                return
            # Eski Qarzdorlik hujjatlarini DB va diskdan o'chiramiz
            try:
                old_paths = await db.delete_info_documents_by_type('Qarzdorlik')
                for p in old_paths:
                    try:
                        if p and os.path.exists(p):
                            os.remove(p)
                    except Exception as ee:
                        logging.warning(f"Eski qarzdorlik faylini o'chirishda ogohlantirish: {ee}")
            except Exception as del_e:
                logging.warning(f"Eski qarzdorlik yozuvlarini o'chirishda ogohlantirish: {del_e}")

            # Ma'lumot hujjati: bitta fayl (Excel) file_path_single
            await db.add_document(
                name_uz=name_uz,
                name_ru=name_ru,
                is_template='false',
                file_path_single=file_path,
                uploaded_by=message.from_user.id,
                document_type='Qarzdorlik',
                expires_at=None,
                category=user_data.get('template_category')
            )
        else:
            # Namuna hujjat: bitta PDF
            await db.add_document(
                name_uz=name_uz,
                name_ru=name_ru,
                is_template='true',
                file_path_uz_pdf=file_path,
                file_path_uz_docx=None,
                file_path_ru_pdf=None,
                file_path_ru_docx=None,
                file_path_single=None,
                uploaded_by=message.from_user.id,
                document_type=None,
                expires_at=None,
                category=user_data.get('template_category')
            )

        await message.answer(texts[lang]['doc_added_success'], reply_markup=get_admin_main_keyboard(lang))
        await state.set_state(MainForm.main_menu)
    except Exception as e:
        logging.error(f"Hujjat qo'shishda xatolik (pdf-only): {e}")
        await message.answer(texts[lang]['doc_add_error'])
        await state.set_state(MainForm.main_menu)


@router.message(AddDocumentForm.waiting_template_uz_docx, F.document)
async def process_template_uz_docx(message: Message, state: FSMContext, bot: Bot):
    """Namuna hujjat - o'zbekcha DOCX"""
    lang = await get_user_lang(state)
    
    if not message.document:
        await message.answer(texts[lang]['doc_add_error'])
        return
    
    file_id = message.document.file_id
    file_info = await bot.get_file(file_id)
    file_bytes_io = await bot.download_file(file_info.file_path)
    
    import os
    os.makedirs('documents/templates', exist_ok=True)
    file_path = f"documents/templates/{message.document.file_name}"
    file_content = file_bytes_io.read()
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_content)
    
    await state.update_data(file_path_uz_docx=file_path)
    await message.answer(texts[lang]['ask_template_ru_pdf'])
    await state.set_state(AddDocumentForm.waiting_template_ru_pdf)


@router.message(AddDocumentForm.waiting_template_ru_pdf, F.document)
async def process_template_ru_pdf(message: Message, state: FSMContext, bot: Bot):
    """Namuna hujjat - ruscha PDF"""
    lang = await get_user_lang(state)
    
    if not message.document:
        await message.answer(texts[lang]['doc_add_error'])
        return
    
    file_id = message.document.file_id
    file_info = await bot.get_file(file_id)
    file_bytes_io = await bot.download_file(file_info.file_path)
    
    import os
    os.makedirs('documents/templates', exist_ok=True)
    file_path = f"documents/templates/{message.document.file_name}"
    file_content = file_bytes_io.read()
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_content)
    
    # Ruscha nomni fayl nomidan olish (agar hali belgilanmagan bo'lsa)
    try:
        base_name = os.path.splitext(message.document.file_name)[0]
    except Exception:
        base_name = None
    if base_name:
        user_data_current = await state.get_data()
        if not user_data_current.get('name_ru'):
            await state.update_data(name_ru=base_name)

    await state.update_data(file_path_ru_pdf=file_path)
    await message.answer(texts[lang]['ask_template_ru_docx'])
    await state.set_state(AddDocumentForm.waiting_template_ru_docx)


@router.message(AddDocumentForm.waiting_template_ru_docx, F.document)
async def process_template_ru_docx(message: Message, state: FSMContext, bot: Bot):
    """Namuna hujjat - ruscha DOCX (oxirgi bosqich)"""
    lang = await get_user_lang(state)
    
    if not message.document:
        await message.answer(texts[lang]['doc_add_error'])
        return
    
    file_id = message.document.file_id
    file_info = await bot.get_file(file_id)
    file_bytes_io = await bot.download_file(file_info.file_path)
    
    import os
    os.makedirs('documents/templates', exist_ok=True)
    file_path = f"documents/templates/{message.document.file_name}"
    file_content = file_bytes_io.read()
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_content)
    
    user_data = await state.get_data()
    
    try:
        doc_id = await db.add_document(
            name_uz=user_data['name_uz'],
            name_ru=user_data['name_ru'],
            is_template='true',
            file_path_uz_pdf=user_data['file_path_uz_pdf'],
            file_path_uz_docx=user_data['file_path_uz_docx'],
            file_path_ru_pdf=user_data['file_path_ru_pdf'],
            file_path_ru_docx=file_path,
            category=user_data.get('template_category'),
            uploaded_by=message.from_user.id
        )
        
        await message.answer(texts[lang]['doc_added_success'], reply_markup=get_admin_main_keyboard(lang))
        await state.set_state(MainForm.main_menu)
        
    except Exception as e:
        logging.error(f"Hujjat qo'shishda xatolik: {e}")
        await message.answer(texts[lang]['doc_add_error'])
        await state.set_state(MainForm.main_menu)


# --- MA'LUMOT HUJJATI QO'SHISH ---

# Ma'lumot hujjatlarda nom va tur talab qilinmaydi
# To'g'ridan-to'g'ri fayl yuklanadi va standart nom bilan saqlanadi


@router.message(AddDocumentForm.waiting_info_file, F.document)
async def process_info_file(message: Message, state: FSMContext, bot: Bot):
    """Ma'lumot hujjati - fayl (oxirgi bosqich)"""
    lang = await get_user_lang(state)
    
    if not message.document:
        await message.answer(texts[lang]['doc_add_error'])
        return
    
    file_id = message.document.file_id
    file_info = await bot.get_file(file_id)
    file_bytes_io = await bot.download_file(file_info.file_path)
    
    import os
    os.makedirs('documents/info', exist_ok=True)
    # Fayl nomidan turli olish (masalan: Qarzdorlik.xlsx -> "Qarzdorlik")
    file_name_without_ext = os.path.splitext(message.document.file_name)[0]
    file_path = f"documents/info/{message.document.file_name}"
    
    # Tanlangan kategoriyani olish
    user_data = await state.get_data()
    selected_category = user_data.get('info_category', 'Umumiy')
    
    # Yangi faylni saqlashdan avval, bir xil kategoriadagi mavjud hujjatlarni o'chiramiz
    try:
        existing_file_paths = []
        from sqlalchemy import select
        from database import Document, async_session_maker
        
        async with async_session_maker() as session:
            result = await session.execute(
                select(Document).where(
                    Document.is_template == 'false',
                    Document.category == selected_category
                )
            )
            docs = result.scalars().all()
            
            for doc in docs:
                if doc.file_path_single:
                    existing_file_paths.append(doc.file_path_single)
                await session.delete(doc)
            
            if docs:
                await session.commit()
                logging.info(f"Eski {selected_category} kategoriyasi hujjatlari o'chirildi: {len(docs)} ta")
        
        # Diskdan ham o'chiramiz
        for old_path in existing_file_paths:
            try:
                if old_path and os.path.exists(old_path):
                    os.remove(old_path)
            except Exception as e:
                logging.warning(f"Eski faylni o'chirishda ogohlantirish: {e}")
    except Exception as e:
        logging.warning(f"Eski ma'lumot hujjatlarini o'chirishda ogohlantirish: {e}")

    # Faylni to'g'ri o'qib diskka yozish
    # file_bytes_io bytesIO obyekti, uni avval o'qiymiz
    import aiofiles
    file_content = file_bytes_io.read()
    
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_content)
    
    try:
        # Ma'lumot hujjat nomi fayl nomidan olinadi (standart)
        # Fayl nomidan extensionsiz qismni olamiz
        doc_name = file_name_without_ext
        
        # Tanlangan kategoriyani yuqorida olingan
        
        await db.add_document(
            name_uz=doc_name,
            name_ru=doc_name,
            category=selected_category,  # Tanlangan kategoriya
            is_template='false',
            file_path_single=file_path,
            uploaded_by=message.from_user.id,
            document_type=selected_category,  # Tanlangan tur
            expires_at=None
        )
        
        await message.answer(texts[lang]['doc_added_success'], reply_markup=get_admin_main_keyboard(lang))
        await state.set_state(MainForm.main_menu)
        
    except Exception as e:
        logging.error(f"Ma'lumot hujjat qo'shishda xatolik: {e}")
        await message.answer(texts[lang]['doc_add_error'])
        await state.set_state(MainForm.main_menu)
