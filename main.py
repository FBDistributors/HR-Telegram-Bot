import asyncio
import logging
import io
import docx
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import os
from dotenv import load_dotenv

load_dotenv()

# --- SOZLAMALAR ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HR_GROUP_ID = os.getenv("HR_GROUP_ID")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- TILLAR UCHUN LUG'AT (TO'LIQ VERSIYASI) ---
texts = {
    'uz': {
        'welcome': "Assalomu alaykum! Muloqot uchun qulay tilni tanlang.",
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
        'welcome': "Здравствуйте! Пожалуйста, выберите удобный язык для общения.",
        'ask_name': "Введите Ваши полные имя и фамилию (например, Салимов Олим).",
        'ask_has_resume': "Отлично! Чтобы продолжить, имеется ли у вас готовое резюме?",
        'button_yes_resume': "✅ Да, отправить резюме",
        'button_no_resume': "❌ Нет, пройти собеседование",
        'prompt_for_resume': "Пожалуйста, отправьте ваше резюме в формате PDF или DOCX.",
        'start_convo_application': "Ничего страшного! Вместо этого, давайте получим информацию о вас через несколько вопросов.",
        'ask_vacancy': "Введите название вакансии, на которую Вы претендуете (например, 'Менеджер по продажам').",
        'ask_experience': "Опишите ваш опыт работы (последнее место работы, должность, сколько лет работали).",
        'ask_salary': "Укажите ваши ожидания по заработной плате? (в сумах, напишите цифрой или текстом)",
        'ask_location': "Введите ваш адрес проживания (город, район).",
        'ask_skills': "Перечислите ваши ключевые навыки для данной позиции (например, Excel, 1C, работа с клиентами).",
        'ask_availability': "Готовы ли вы приступить к работе в ближайшее время?",
        'button_yes': "✅ Да",
        'button_no': "❌ Нет",
        'ask_contact': "Для связи, пожалуйста, отправьте ваш номер телефона с помощью кнопки ниже:",
        'button_share_contact': "📱 Поделиться моим контактом",
        'goodbye_user': "Спасибо за все данные! Ваша заявка успешно принята. Мы свяжемся с вами в ближайшее время, если ваша кандидатура будет одобрена. ✅",
        'analyzing': "Данные получены. Сейчас они анализируются с помощью искусственного интеллекта, подождите немного...",
        'file_error': "Пожалуйста, отправьте резюме только в формате PDF или DOCX.",
        'hr_notification_file': """🔔 **Новый кандидат (с резюме)!**

👤 **ФИО:** {name}
📄 **Резюме:** Файл прикреплен.
-------------------
{summary}""",
        'hr_notification_convo': """🔔 **Новый кандидат (через чат)!**

👤 **ФИО:** {name}
👨‍💼 **Вакансия:** {vacancy}
-------------------
**Ответы кандидата:**
- **Опыт:** {experience}
- **Ожидаемая зарплата:** {salary}
- **Адрес:** {location}
- **Навыки:** {skills}
- **Готовность к работе:** {availability}
- **Контакт:** {contact}
-------------------
{summary}""",
        'gemini_file_prompt': """Ты опытный HR-менеджер. Приложенный PDF-файл является резюме кандидата. 
        Прочитай это резюме и напиши краткое и четкое заключение о кандидате на русском языке.
        Анализ должен быть в следующем формате, используй эмодзи для заголовков и списков:
        🤖 **Общее заключение:** [Заключение из 2-3 предложений на основе опыта, навыков и образования кандидата]
        ✨ **Сильные стороны:**
        ✅ [Первая ключевая сильная сторона, найденная в резюме]
        ✅ [Вторая ключевая сильная сторона, найденная в резюме]
        📊 **Предварительная оценка:** [Подходит / Стоит рассмотреть / Недостаточно опыта]""",
        'gemini_text_prompt': """Ты опытный HR-менеджер. Ниже приведен текст из резюме кандидата. 
        Проанализируй этот текст и напиши краткое и четкое заключение о кандидате на русском языке.
        Анализ должен быть в следующем формате, используй эмодзи для заголовков и списков:
        🤖 **Общее заключение:** [Заключение из 2-3 предложений на основе опыта, навыков и образования кандидата]
        ✨ **Сильные стороны:**
        ✅ [Первая ключевая сильная сторона, найденная в резюме]
        ✅ [Вторая ключевая сильная сторона, найденная в резюме]
        📊 **Предварительная оценка:** [Подходит / Стоит рассмотреть / Недостаточно опыта]
        
        Текст резюме:
        {resume_text}
        """,
        'gemini_convo_prompt': """Ты опытный HR-менеджер. Ниже приведены ответы кандидата из чата. 
        Проанализируй эту информацию и напиши краткое и четкое заключение о кандидате на русском языке.
        Анализ должен быть в следующем формате, используй эмодзи:
        🤖 **Общее заключение:** [Заключение из 2-3 предложений на основе ответов кандидата и соответствия вакансии]
        ✨ **Сильные стороны:**
        ✅ [Первая ключевая сильная сторона, найденная в ответах]
        ✅ [Вторая ключевая сильная сторона, найденная в ответах]
        📊 **Предварительная оценка:** [Подходит / Стоит рассмотреть / Недостаточно опыта]"""
    }
}


# --- BOTNING XOTIRASI (FSM) YANGILANDI ---
class Form(StatesGroup):
    language_selection = State()
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

# --- ASOSIY BOT QISMI ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')

# --- BOT SUHBATLOGIKASI (QAYTA QURILDI) ---
@dp.message(Command("start"))
async def send_welcome(message: types.Message, state: FSMContext):
    await state.clear()
    language_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")], [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")]])
    await message.reply(f"{texts['uz']['welcome']}\n{texts['ru']['welcome']}", reply_markup=language_keyboard)
    await state.set_state(Form.language_selection)

@dp.callback_query(Form.language_selection, F.data.startswith('lang_'))
async def process_language_selection(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split('_')[1]
    await state.update_data(language=lang)
    await callback.message.delete_reply_markup()
    await callback.message.answer(texts[lang]['ask_name'])
    await state.set_state(Form.name)
    await callback.answer()

@dp.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(name=message.text)
    
    resume_choice_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts[lang]['button_yes_resume'], callback_data="has_resume_yes")],
        [InlineKeyboardButton(text=texts[lang]['button_no_resume'], callback_data="has_resume_no")]
    ])
    await message.answer(texts[lang]['ask_has_resume'], reply_markup=resume_choice_keyboard)
    await state.set_state(Form.has_resume_choice)

@dp.callback_query(Form.has_resume_choice, F.data.startswith('has_resume_'))
async def process_has_resume_choice(callback: types.CallbackQuery, state: FSMContext):
    lang = await get_user_lang(state)
    choice = callback.data.split('_')[2]
    await callback.message.delete_reply_markup()
    
    if choice == "yes":
        await callback.message.answer(texts[lang]['prompt_for_resume'])
        await state.set_state(Form.resume_upload)
    elif choice == "no":
        await callback.message.answer(texts[lang]['start_convo_application'])
        await callback.message.answer(texts[lang]['ask_vacancy'])
        await state.set_state(Form.convo_vacancy)
    await callback.answer()

# === 1-YO'L: Rezyume yuklash uchun handler ===
@dp.message(Form.resume_upload, F.document)
async def process_resume_file(message: types.Message, state: FSMContext):
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
            resume_text_parts = []
            for para in document.paragraphs: resume_text_parts.append(para.text)
            for table in document.tables:
                for row in table.rows:
                    for cell in row.cells: resume_text_parts.append(cell.text)
            resume_text = "\n".join(resume_text_parts)
            
            if not resume_text.strip():
                 gemini_summary = "DOCX faylidan matn topilmadi."
            else:
                prompt = texts[lang]['gemini_text_prompt'].format(resume_text=resume_text)
                response = await model.generate_content_async(prompt)
                gemini_summary = response.text
    except Exception as e:
        logging.error(f"Faylni tahlil qilishdagi xato: {e}")
        gemini_summary = "Faylni tahlil qilishda xatolik yuz berdi."

    hr_notification_template = texts[lang]['hr_notification_file']
    hr_summary_text = hr_notification_template.format(name=user_data.get('name'), summary=gemini_summary)
    
    if HR_GROUP_ID:
        await bot.send_message(HR_GROUP_ID, hr_summary_text, parse_mode="Markdown")
        await bot.send_document(HR_GROUP_ID, file_id)
    
    await message.answer(texts[lang]['goodbye_user'])
    await state.clear()


# === 2-YO'L: Suhbat orqali ma'lumot olish ===
@dp.message(Form.convo_vacancy)
async def process_convo_vacancy(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(vacancy=message.text)
    await message.answer(texts[lang]['ask_experience'])
    await state.set_state(Form.convo_experience)

@dp.message(Form.convo_experience)
async def process_convo_experience(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(experience=message.text)
    await message.answer(texts[lang]['ask_salary'])
    await state.set_state(Form.convo_salary)

@dp.message(Form.convo_salary)
async def process_convo_salary(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(salary=message.text)
    await message.answer(texts[lang]['ask_location'])
    await state.set_state(Form.convo_location)

@dp.message(Form.convo_location)
async def process_convo_location(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(location=message.text)
    await message.answer(texts[lang]['ask_skills'])
    await state.set_state(Form.convo_skills)

@dp.message(Form.convo_skills)
async def process_convo_skills(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(skills=message.text)
    availability_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts[lang]['button_yes'], callback_data="availability_yes")],
        [InlineKeyboardButton(text=texts[lang]['button_no'], callback_data="availability_no")]
    ])
    await message.answer(texts[lang]['ask_availability'], reply_markup=availability_keyboard)
    await state.set_state(Form.convo_availability)

@dp.callback_query(Form.convo_availability, F.data.startswith('availability_'))
async def process_convo_availability(callback: types.CallbackQuery, state: FSMContext):
    lang = await get_user_lang(state)
    choice = callback.data.split('_')[1]
    availability_text = texts[lang]['button_yes'] if choice == "yes" else texts[lang]['button_no']
    
    await state.update_data(availability=availability_text)
    await callback.message.delete_reply_markup()
    
    # Maxsus klaviatura yaratish
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts[lang]['button_share_contact'], request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await callback.message.answer(texts[lang]['ask_contact'], reply_markup=contact_keyboard)
    await state.set_state(Form.convo_contact)
    await callback.answer()

# KONTAKTNI QABUL QILADIGAN funksiya
@dp.message(Form.convo_contact, F.contact)
async def process_convo_contact(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    contact_number = message.contact.phone_number
    await state.update_data(contact=contact_number)
    
    # Maxsus klaviaturani olib tashlash
    await message.answer(f"Raqamingiz qabul qilindi: {contact_number}", reply_markup=ReplyKeyboardRemove())
    
    await message.answer(texts[lang]['analyzing'])

    user_data = await state.get_data()
    
    # ... (Bu yerdagi Gemini tahlili va HR guruhiga yuborish logikasi o'zgarishsiz qoladi) ...
    
    candidate_summary_text = (
        f"Vakansiya: {user_data.get('vacancy')}\n"
        f"Tajribasi: {user_data.get('experience')}\n"
        f"Maosh kutilmasi: {user_data.get('salary')}\n"
        f"Manzili: {user_data.get('location')}\n"
        f"Ko'nikmalari: {user_data.get('skills')}\n"
        f"Ishga tayyorligi: {user_data.get('availability')}\n"
        f"Aloqa: {user_data.get('contact')}"
    )
    
    prompt = texts[lang]['gemini_convo_prompt']
    full_prompt = f"{prompt}\n\nNomzod javoblari:\n{candidate_summary_text}"
    
    response = await model.generate_content_async(full_prompt)
    gemini_summary = response.text
    
    hr_notification_template = texts[lang]['hr_notification_convo']
    hr_summary_text = hr_notification_template.format(**user_data, summary=gemini_summary)

    if HR_GROUP_ID:
        await bot.send_message(HR_GROUP_ID, hr_summary_text, parse_mode="Markdown")

    await message.answer(texts[lang]['goodbye_user'])
    await state.clear()

async def main():
    if not BOT_TOKEN or not GEMINI_API_KEY:
        logging.critical("Bot tokeni yoki Gemini API kaliti topilmadi!")
        return
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())