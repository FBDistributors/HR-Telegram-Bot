# ariza_topshirish.py fayli (Ko'p tilli tizim bilan to'liq ishlaydigan versiya)

import logging
import io
import docx
import os
import google.generativeai as genai

from aiogram import Bot, Router, F, types
from aiogram.fsm.context import FSMContext

# Yangi states va keyboards fayllaridan import qilish
from states import MainForm, AppForm
from keyboards import texts, get_user_keyboard, get_admin_keyboard

router = Router()

# Sozlamalar
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HR_GROUP_ID = os.getenv("HR_GROUP_ID")
ADMIN_ID = os.getenv("ADMIN_ID")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')

# --- ARIZA BO'LIMI HANDLER'LARI ---

@router.message(AppForm.name, F.text)
async def process_name(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(name=message.text)
    
    # --- MUHIM TUZATISH: Matnlar endi keyboards.py dan olinadi ---
    resume_choice_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=texts[lang]['has_resume_yes_button'], callback_data="has_resume_yes")],
        [types.InlineKeyboardButton(text=texts[lang]['has_resume_no_button'], callback_data="has_resume_no")]
    ])
    await message.answer(texts[lang]['ask_has_resume'], reply_markup=resume_choice_keyboard)
    await state.set_state(AppForm.has_resume_choice)

@router.callback_query(AppForm.has_resume_choice, F.data.startswith('has_resume_'))
async def process_has_resume_choice(callback: types.CallbackQuery, state: FSMContext):
    lang = await get_user_lang(state)
    choice = callback.data.split('_')[2]
    await callback.message.delete_reply_markup()
    
    # Bu qismdagi matnlar ham kelajakda keyboards.py ga o'tkazilishi mumkin
    if choice == "yes":
        await callback.message.answer(texts[lang]['prompt_for_resume'])
        await state.set_state(AppForm.resume_upload)
    elif choice == "no":
        await callback.message.answer(texts[lang]['start_convo_application'])
        await callback.message.answer(texts[lang]['ask_vacancy'])
        await state.set_state(AppForm.convo_vacancy)
    await callback.answer()


# === 1-YO'L: Rezyume faylini qayta ishlash ===
@router.message(AppForm.resume_upload, F.document)
async def process_resume_file(message: types.Message, state: FSMContext, bot: Bot):
    lang = await get_user_lang(state)
    file_mime_type = message.document.mime_type
    
    if file_mime_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        await message.reply(texts[lang]['file_format_error'])
        return

    await message.answer(texts[lang]['analyzing_resume'])
    
    file_id = message.document.file_id
    file_info = await bot.get_file(file_id)
    file_bytes_io = await bot.download_file(file_info.file_path)
    
    user_data = await state.get_data()
    gemini_summary = "Faylni tahlil qilishda xatolik yuz berdi."

    if GEMINI_API_KEY:
        try:
            prompt = texts[lang]['gemini_file_prompt']
            
            if file_mime_type == "application/pdf":
                pdf_part = {"mime_type": "application/pdf", "data": file_bytes_io.read()}
                response = await model.generate_content_async([prompt, pdf_part])
                gemini_summary = response.text
            
            elif file_mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                document = docx.Document(file_bytes_io)
                resume_text = "\n".join([para.text for para in document.paragraphs])
                
                if not resume_text.strip():
                    gemini_summary = "DOCX faylidan matn topilmadi."
                else:
                    full_prompt = f"{prompt}\n\nRezyume matni:\n{resume_text}"
                    response = await model.generate_content_async(full_prompt)
                    gemini_summary = response.text
        except Exception as e:
            logging.error(f"Faylni tahlil qilishdagi xato: {e}")

    hr_notification_text = (
        f"🔔 **Yangi nomzod (Rezyume bilan)!**\n\n"
        f"👤 **FIO:** {user_data.get('name')}\n"
        f"-------------------\n"
        f"{gemini_summary}"
    )
    
    if HR_GROUP_ID:
        try:
            await bot.send_message(HR_GROUP_ID, hr_notification_text, parse_mode="Markdown")
            await bot.send_document(HR_GROUP_ID, file_id)
        except Exception as e:
            logging.error(f"HR guruhiga fayl yuborishda xato: {e}")

    await message.answer(texts[lang]['application_thanks'])
    
    if str(message.from_user.id) == ADMIN_ID:
        keyboard = get_admin_keyboard(lang)
    else:
        keyboard = get_user_keyboard(lang)
        
    await message.answer(texts[lang]['welcome_menu'], reply_markup=keyboard)
    await state.set_state(MainForm.main_menu)


# === 2-YO'L: Suhbat orqali ma'lumot olish (to'liq versiya) ===
@router.message(AppForm.convo_vacancy)
async def process_convo_vacancy(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(vacancy=message.text)
    await message.answer(texts[lang]['ask_experience'])
    await state.set_state(AppForm.convo_experience)

@router.message(AppForm.convo_experience)
async def process_convo_experience(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(experience=message.text)
    await message.answer(texts[lang]['ask_salary'])
    await state.set_state(AppForm.convo_salary)

@router.message(AppForm.convo_salary)
async def process_convo_salary(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(salary=message.text)
    await message.answer(texts[lang]['ask_location'])
    await state.set_state(AppForm.convo_location)

@router.message(AppForm.convo_location)
async def process_convo_location(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(location=message.text)
    await message.answer(texts[lang]['ask_skills'])
    await state.set_state(AppForm.convo_skills)

@router.message(AppForm.convo_skills)
async def process_convo_skills(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(skills=message.text)
    availability_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=texts[lang]['availability_yes_button'], callback_data="availability_yes")],
        [types.InlineKeyboardButton(text=texts[lang]['availability_no_button'], callback_data="availability_no")]
    ])
    await message.answer(texts[lang]['ask_availability'], reply_markup=availability_keyboard)
    await state.set_state(AppForm.convo_availability)

@router.callback_query(AppForm.convo_availability, F.data.startswith('availability_'))
async def process_convo_availability(callback: types.CallbackQuery, state: FSMContext):
    lang = await get_user_lang(state)
    choice = callback.data.split('_')[1]
    availability_text = texts[lang]['availability_yes_button'] if choice == "yes" else texts[lang]['availability_no_button']
    
    await state.update_data(availability=availability_text)
    await callback.message.delete_reply_markup()
    
    contact_keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=texts[lang]['button_share_contact'], request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await callback.message.answer(texts[lang]['ask_contact'], reply_markup=contact_keyboard)
    await state.set_state(AppForm.convo_contact)
    await callback.answer()

@router.message(AppForm.convo_contact, F.contact)
async def process_convo_contact(message: types.Message, state: FSMContext, bot: Bot):
    lang = await get_user_lang(state)
    await state.update_data(contact=message.contact.phone_number)
    
    await message.answer(texts[lang]['analyzing_convo'], reply_markup=types.ReplyKeyboardRemove())
    
    user_data = await state.get_data()
    
    candidate_summary_text = (
        f"- **Tajribasi:** {user_data.get('experience')}\n"
        f"- **Maosh kutilmasi:** {user_data.get('salary')}\n"
        f"- **Manzili:** {user_data.get('location')}\n"
        f"- **Ko'nikmalari:** {user_data.get('skills')}\n"
        f"- **Ishga tayyorligi:** {user_data.get('availability')}\n"
        f"- **Aloqa:** {user_data.get('contact')}"
    )
    
    gemini_summary = "Nomzod haqida AI xulosasini yaratib bo'lmadi."
    if GEMINI_API_KEY:
        try:
            prompt = texts[lang]['gemini_convo_prompt'].format(candidate_summary=candidate_summary_text)
            response = await model.generate_content_async(prompt)
            gemini_summary = response.text
        except Exception as e:
            logging.error(f"Suhbatni tahlil qilishdagi xato: {e}")

    hr_notification_text = (
        f"🔔 **Yangi nomzod (Suhbat orqali)!**\n\n"
        f"👤 **FIO:** {user_data.get('name')}\n"
        f"👨‍💼 **Vakansiya:** {user_data.get('vacancy')}\n"
        f"-------------------\n"
        f"**Nomzod javoblari:**\n"
        f"{candidate_summary_text}\n"
        f"-------------------\n"
        f"{gemini_summary}"
    )

    if HR_GROUP_ID:
        try:
            await bot.send_message(HR_GROUP_ID, hr_notification_text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"HR guruhiga xabar yuborishda xato: {e}")

    await message.answer(texts[lang]['application_thanks'])
    
    if str(message.from_user.id) == ADMIN_ID:
        keyboard = get_admin_keyboard(lang)
    else:
        keyboard = get_user_keyboard(lang)
        
    await message.answer(texts[lang]['welcome_menu'], reply_markup=keyboard)
    await state.set_state(MainForm.main_menu)
