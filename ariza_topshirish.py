# ariza_topshirish.py fayli (Ariza qabul qilish bo'limi)

import logging
import io
import docx  # Bu kutubxonani o'rnatish kerak: pip install python-docx
import os
import google.generativeai as genai

from aiogram import Bot, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

# --- BU FAYL UCHUN ALOHIDA ROUTER YARATAMIZ ---
router = Router()

# --- Sozlamalar va Konfiguratsiya ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HR_GROUP_ID = os.getenv("HR_GROUP_ID")

if not GEMINI_API_KEY:
    logging.critical("Ariza bo'limi uchun Gemini API kaliti topilmadi!")
else:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

# --- TILLAR UCHUN LUG'AT ---
# (Siz taqdim etgan to'liq lug'at bu yerda bo'lishi kerak. Qisqalik uchun uni qoldirib ketdim)
# ... texts lug'ati ...
texts = {
    'uz': {
        'ask_name': "To'liq ism-sharifingizni kiriting (masalan, Olimov Salim).",
        'ask_has_resume': "Rahmat. Arizani davom ettirish uchun tayyor rezyumeingiz mavjudmi?",
        'button_yes_resume': "✅ Ha, rezyume yuborish",
        'button_no_resume': "❌ Yo'q, suhbatdan o'tish",
        'prompt_for_resume': "Marhamat, rezyumeni PDF yoki DOCX formatida yuboring.",
        'start_convo_application': "Hechqisi yo'q! Keling, o'rniga bir nechta savollar orqali siz haqingizda ma'lumot olamiz.",
        'ask_vacancy': "Murojaat qilayotgan vakansiya nomini kiriting (masalan, Buxgalter).",
        'ask_experience': "Ish tajribangiz haqida yozing (oxirgi ish joyingiz, lavozimingiz, necha yil ishlaganingiz).",
        'ask_salary': "Oylik maosh bo'yicha kutilmalaringizni kiriting (so'mda, raqam yoki matn bilan yozing)",
        'ask_location': "Yashash manzilingizni kiriting (shahar, tuman).",
        'ask_skills': "Lavozimga oid eng muhim ko'nikmalaringizni sanab o'ting (masalan, Excel, 1C, mijozlar bilan ishlash).",
        'ask_availability': "Yaqin kunlarda ish boshlashga tayyormisiz?",
        'button_yes': "✅ Ha",
        'button_no': "❌ Yo'q",
        'ask_contact': "Siz bilan bog'lanish uchun, quyidagi tugma orqali telefon raqamingizni yuboring:",
        'button_share_contact': "📱 Kontaktimni ulashish",
        'goodbye_user': "Barcha ma'lumotlaringiz uchun rahmat! Arizangiz muvaffaqiyatli qabul qilindi. Nomzodingiz ma'qul topilsa, biz siz bilan tez orada bog'lanamiz. ✅",
        'analyzing': "Ma'lumotlar qabul qilindi. Hozir sun'iy intellekt yordamida tahlil qilinmoqda, bir oz kuting...",
        'file_error': "Iltimos, rezyumeni faqat PDF yoki DOCX formatida yuboring.",
        'hr_notification_file': """🔔 **Yangi nomzod (Rezyume bilan)!**

👤 **FIO:** {name}
📄 **Rezyume:** Fayl biriktirildi.
-------------------
{summary}""",
        'hr_notification_convo': """🔔 **Yangi nomzod (Suhbat orqali)!**

👤 **FIO:** {name}
👨‍💼 **Vakansiya:** {vacancy}
-------------------
**Nomzod javoblari:**
- **Tajribasi:** {experience}
- **Maosh kutilmasi:** {salary}
- **Manzili:** {location}
- **Ko'nikmalari:** {skills}
- **Ishga tayyorligi:** {availability}
- **Aloqa:** {contact}
-------------------
{summary}""",
        'gemini_file_prompt': """Sen tajribali HR-menejersan. Ilova qilingan fayl nomzodning rezyumesi hisoblanadi. 
        Ushbu rezyumeni o'qib chiqib, nomzod haqida o'zbek tilida, lotin alifbosida qisqacha va aniq xulosa yoz.
        Tahlil quyidagi formatda bo'lsin, sarlavhalar va ro'yxatlar uchun emoji'lardan foydalan:
        🤖 **Umumiy xulosa:** [Nomzodning tajribasi, ko'nikmalari va ma'lumotlari asosida 2-3 gaplik xulosa]
        ✨ **Kuchli tomonlari:**
        ✅ [Rezyumedan topilgan birinchi kuchli jihat]
        ✅ [Rezyumedan topilgan ikkinchi kuchli jihat]
        📊 **Dastlabki baho:** [Mos keladi / O'ylab ko'rish kerak / Tajribasi kam]""",
        'gemini_text_prompt': """Sen tajribali HR-menejersan. Quyida nomzodning rezyumesidan olingan matn keltirilgan. 
        Ushbu matnni tahlil qilib, nomzod haqida o'zbek tilida, lotin alifbosida qisqacha va aniq xulosa yoz.
        Tahlil quyidagi formatda bo'lsin, sarlavhalar va ro'yxatlar uchun emoji'lardan foydalan:
        🤖 **Umumiy xulosa:** [Nomzodning tajribasi, ko'nikmalari va ma'lumotlari asosida 2-3 gaplik xulosa]
        ✨ **Kuchli tomonlari:**
        ✅ [Rezyumedan topilgan birinchi kuchli jihat]
        ✅ [Rezyumedan topilgan ikkinchi kuchli jihat]
        📊 **Dastlabki baho:** [Mos keladi / O'ylab ko'rish kerak / Tajribasi kam]
        
        Rezyume matni:
        {resume_text}
        """,
        'gemini_convo_prompt': """Sen tajribali HR-menejersan. Quyida nomzodning suhbat orqali bergan javoblari keltirilgan. 
        Ushbu ma'lumotlarni tahlil qilib, nomzod haqida o'zbek tilida, lotin alifbosida qisqacha va aniq xulosa yoz.
        Tahlil quyidagi formatda bo'lsin, emoji'lardan foydalan:
        🤖 **Umumiy xulosa:** [Nomzodning javoblari va vakansiyaga mosligi asosida 2-3 gaplik xulosa]
        ✨ **Kuchli tomonlari:**
        ✅ [Suhbatdan topilgan birinchi kuchli jihat]
        ✅ [Suhbatdan topilgan ikkinchi kuchli jihat]
        📊 **Dastlabki baho:** [Mos keladi / O'ylab ko'rish kerak / Tajribasi kam]"""
    },
    'ru': {
        # ... ruscha versiya ...
    }
}


# --- ARIZA UCHUN FSM HOLATLARI ---
class AppForm(StatesGroup):
    name = State()
    has_resume_choice = State()
    resume_upload = State()
    convo_vacancy = State()
    convo_experience = State()
    convo_salary = State()
    convo_location = State()
    convo_skills = State()
    convo_availability = State()
    convo_contact = State()

# Foydalanuvchi tanlagan tilni olish uchun yordamchi funksiya
async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')


# --- ARIZA BO'LIMI HANDLER'LARI ---

# Ism-sharifni qabul qilish
@router.message(AppForm.name, F.text)
async def process_name(message: Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(name=message.text)
    
    resume_choice_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts[lang]['button_yes_resume'], callback_data="has_resume_yes")],
        [InlineKeyboardButton(text=texts[lang]['button_no_resume'], callback_data="has_resume_no")]
    ])
    await message.answer(texts[lang]['ask_has_resume'], reply_markup=resume_choice_keyboard)
    await state.set_state(AppForm.has_resume_choice)

# Rezyume bor/yo'qligini aniqlash
@router.callback_query(AppForm.has_resume_choice, F.data.startswith('has_resume_'))
async def process_has_resume_choice(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(state)
    choice = callback.data.split('_')[2]
    await callback.message.delete_reply_markup()
    
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
async def process_resume_file(message: Message, state: FSMContext, bot: Bot):
    if not GEMINI_API_KEY:
        await message.reply("Kechirasiz, fayllarni tahlil qilish moduli sozlanmagan.")
        return

    lang = await get_user_lang(state)
    file_mime_type = message.document.mime_type
    
    if file_mime_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        await message.reply(texts[lang]['file_error'])
        return

    await message.answer(texts[lang]['analyzing'])
    
    file_id = message.document.file_id
    file_info = await bot.get_file(file_id)
    file_bytes_io = await bot.download_file(file_info.file_path)
    
    user_data = await state.get_data()
    gemini_summary = ""

    try:
        if file_mime_type == "application/pdf":
            pdf_part = {"mime_type": "application/pdf", "data": file_bytes_io.read()}
            prompt = texts[lang]['gemini_file_prompt']
            response = await model.generate_content_async([prompt, pdf_part])
            gemini_summary = response.text
        elif file_mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            document = docx.Document(file_bytes_io)
            resume_text = "\n".join([para.text for para in document.paragraphs])
            
            if not resume_text.strip():
                gemini_summary = "DOCX faylidan matn topilmadi."
            else:
                prompt = texts[lang]['gemini_text_prompt'].format(resume_text=resume_text)
                response = await model.generate_content_async(prompt)
                gemini_summary = response.text
    except Exception as e:
        logging.error(f"Faylni tahlil qilishdagi xato: {e}")
        gemini_summary = "Faylni tahlil qilishda xatolik yuz berdi."

    hr_notification = texts[lang]['hr_notification_file'].format(name=user_data.get('name'), summary=gemini_summary)
    
    if HR_GROUP_ID:
        try:
            await bot.send_message(HR_GROUP_ID, hr_notification, parse_mode="Markdown")
            await bot.send_document(HR_GROUP_ID, file_id)
        except Exception as e:
            logging.error(f"HR guruhiga xabar yuborishda xato: {e}")
    
    await message.answer(texts[lang]['goodbye_user'])
    await state.clear()

# === 2-YO'L: Suhbat orqali ma'lumot olish ===
# ... (Bu qismdagi kodlar deyarli o'zgarishsiz qoladi, faqat @dp. o'rniga @router. ishlatiladi)
@router.message(AppForm.convo_vacancy)
async def process_convo_vacancy(message: Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(vacancy=message.text)
    await message.answer(texts[lang]['ask_experience'])
    await state.set_state(AppForm.convo_experience)

# ... qolgan suhbat handler'lari xuddi shunday davom etadi ...

@router.message(AppForm.convo_experience)
async def process_convo_experience(message: Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(experience=message.text)
    await message.answer(texts[lang]['ask_salary'])
    await state.set_state(AppForm.convo_salary)

@router.message(AppForm.convo_salary)
async def process_convo_salary(message: Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(salary=message.text)
    await message.answer(texts[lang]['ask_location'])
    await state.set_state(AppForm.convo_location)

@router.message(AppForm.convo_location)
async def process_convo_location(message: Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(location=message.text)
    await message.answer(texts[lang]['ask_skills'])
    await state.set_state(AppForm.convo_skills)

@router.message(AppForm.convo_skills)
async def process_convo_skills(message: Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(skills=message.text)
    availability_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts[lang]['button_yes'], callback_data="availability_yes")],
        [InlineKeyboardButton(text=texts[lang]['button_no'], callback_data="availability_no")]
    ])
    await message.answer(texts[lang]['ask_availability'], reply_markup=availability_keyboard)
    await state.set_state(AppForm.convo_availability)

@router.callback_query(AppForm.convo_availability, F.data.startswith('availability_'))
async def process_convo_availability(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(state)
    choice = callback.data.split('_')[1]
    availability_text = texts[lang]['button_yes'] if choice == "yes" else texts[lang]['button_no']
    
    await state.update_data(availability=availability_text)
    await callback.message.delete_reply_markup()
    
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts[lang]['button_share_contact'], request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    
    await callback.message.answer(texts[lang]['ask_contact'], reply_markup=contact_keyboard)
    await state.set_state(AppForm.convo_contact)
    await callback.answer()

# Kontaktni qabul qilish va jarayonni yakunlash
@router.message(AppForm.convo_contact, F.contact)
async def process_convo_contact(message: Message, state: FSMContext, bot: Bot):
    if not GEMINI_API_KEY:
        await message.reply("Kechirasiz, tahlil moduli sozlanmagan.")
        return
        
    lang = await get_user_lang(state)
    await state.update_data(contact=message.contact.phone_number)
    
    await message.answer(f"Raqamingiz qabul qilindi.", reply_markup=ReplyKeyboardRemove())
    await message.answer(texts[lang]['analyzing'])

    user_data = await state.get_data()
    
    candidate_info = "\n".join([
        f"- **Vakansiya:** {user_data.get('vacancy', 'N/A')}",
        f"- **Tajribasi:** {user_data.get('experience', 'N/A')}",
        f"- **Maosh kutilmasi:** {user_data.get('salary', 'N/A')}",
        f"- **Manzili:** {user_data.get('location', 'N/A')}",
        f"- **Ko'nikmalari:** {user_data.get('skills', 'N/A')}",
        f"- **Ishga tayyorligi:** {user_data.get('availability', 'N/A')}",
    ])
    
    prompt = f"{texts[lang]['gemini_convo_prompt']}\n\nNomzod javoblari:\n{candidate_info}"
    
    gemini_summary = "Suhbatni tahlil qilishda xatolik yuz berdi."
    try:
        response = await model.generate_content_async(prompt)
        gemini_summary = response.text
    except Exception as e:
        logging.error(f"Suhbatni tahlil qilishdagi xato: {e}")

    hr_notification = texts[lang]['hr_notification_convo'].format(**user_data, summary=gemini_summary)

    if HR_GROUP_ID:
        try:
            await bot.send_message(HR_GROUP_ID, hr_notification, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"HR guruhiga xabar yuborishda xato: {e}")

    await message.answer(texts[lang]['goodbye_user'])
    await state.clear()
