import asyncio
import logging
import io
import docx
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
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

# --- TILLAR UCHUN LUG'AT (YANGILANGAN) ---
texts = {
    'uz': {
        'welcome': "Assalomu alaykum! Tilni tanlang.",
        'ask_name': "To'liq ism-familiyangizni kiriting:",
        'ask_has_resume': "Ajoyib! Arizani davom ettirish uchun, rezyumeingiz bormi?",
        'button_yes_resume': "✅ Ha, bor",
        'button_no_resume': "❌ Yo'q, hozir yo'q",
        'prompt_for_resume': "Marhamat, rezyumeni PDF yoki DOCX formatida yuboring.",
        'start_convo_application': "Hechqisi yo'q! Keling, suhbat orqali bir nechta savollarga javob bering.",
        'ask_experience_convo': "Oxirgi ish joyingiz va tajribangiz haqida yozing (masalan, 'Kompaniya nomi, Analitik, 2 yil').",
        'ask_skills_convo': "Qaysi sohalarda kuchli ko'nikmalarga egasiz (masalan, 'SMM, Python, Sotuv').",
        'ask_contact_convo': "Siz bilan bog'lanish uchun telefon raqamingiz yoki emailingizni kiriting.",
        'analyzing': "Ma'lumotlar qabul qilindi. Hozir sun'iy intellekt yordamida tahlil qilinmoqda, bir oz kuting...",
        'goodbye_user': "Arizangiz uchun rahmat! Ma'lumotlaringiz muvaffaqiyatli qabul qilindi. Agar nomzodingiz ma'qul topilsa, biz siz bilan tez orada bog'lanamiz. ✅",
        'file_error': "Iltimos, rezyumeni faqat PDF yoki DOCX formatida yuboring.",
        'hr_notification_file': """🔔 **Yangi nomzod (Rezyume bilan)!**

👤 **Ism:** {name}
📄 **Rezyume:** Fayl biriktirildi.
-------------------
{summary}""",
        'hr_notification_convo': """🔔 **Yangi nomzod (Suhbat orqali)!**

👤 **Ism:** {name}
📝 **Tajribasi:** {experience}
🛠 **Ko'nikmalari:** {skills}
📞 **Aloqa:** {contact}
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
        'gemini_convo_prompt': """Sen tajribali HR-menejersan. Quyida nomzodning suhbat orqali bergan javoblari keltirilgan. 
        Ushbu ma'lumotlarni tahlil qilib, nomzod haqida o'zbek tilida, lotin alifbosida qisqacha va aniq xulosa yoz.
        Tahlil quyidagi formatda bo'lsin, emoji'lardan foydalan:
        🤖 **Umumiy xulosa:** [Nomzodning javoblari asosida 2-3 gaplik xulosa]
        ✨ **Kuchli tomonlari:**
        ✅ [Suhbatdan topilgan birinchi kuchli jihat]
        ✅ [Suhbatdan topilgan ikkinchi kuchli jihat]
        📊 **Dastlabki baho:** [Mos keladi / O'ylab ko'rish kerak / Tajribasi kam]"""
    },
    'ru': { # Ruscha versiya ham xuddi shunday to'ldirilishi kerak
        'welcome': "Здравствуйте! Выберите язык.",
        'ask_name': "Введите ваше полное имя и фамилию:",
        'ask_has_resume': "Отлично! Чтобы продолжить, есть ли у вас резюме?",
        'button_yes_resume': "✅ Да, есть",
        'button_no_resume': "❌ Нет, сейчас нет",
        'prompt_for_resume': "Пожалуйста, отправьте ваше резюме в формате PDF или DOCX.",
        'start_convo_application': "Ничего страшного! Давайте ответим на несколько вопросов в чате.",
        'ask_experience_convo': "Расскажите о вашем последнем месте работы и опыте (например, 'Название компании, Аналитик, 2 года').",
        'ask_skills_convo': "В каких областях у вас есть сильные навыки (например, 'SMM, Python, Продажи').",
        'ask_contact_convo': "Введите ваш номер телефона или email для связи.",
        'analyzing': "Данные получены. Сейчас они анализируются...",
        'goodbye_user': "Спасибо за вашу заявку! Ваши данные успешно приняты. Мы свяжемся с вами. ✅",
        'file_error': "Пожалуйста, отправьте резюме только в формате PDF или DOCX.",
        'hr_notification_file': """🔔 **Новый кандидат (с резюме)!**

👤 **Имя:** {name}
📄 **Резюме:** Файл прикреплен.
-------------------
{summary}""",
        'hr_notification_convo': """🔔 **Новый кандидат (через чат)!**

👤 **Имя:** {name}
📝 **Опыт:** {experience}
🛠 **Навыки:** {skills}
📞 **Контакт:** {contact}
-------------------
{summary}""",
        'gemini_convo_prompt': """...""" # Ruscha versiyasi
    }
}

# --- BOTNING XOTIRASI (FSM) YANGILANDI ---
class Form(StatesGroup):
    language_selection = State()
    name = State()
    has_resume_choice = State()  # Rezyume bor-yo'qligini so'rash holati
    resume_upload = State()      # Rezyumeni kutish holati
    convo_experience = State()   # Suhbat: tajribani kutish
    convo_skills = State()       # Suhbat: ko'nikmalarni kutish
    convo_contact = State()      # Suhbat: aloqa ma'lumotini kutish

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
        await callback.message.answer(texts[lang]['ask_experience_convo'])
        await state.set_state(Form.convo_experience)
    await callback.answer()

# === 1-YO'L: Rezyume yuklash uchun handler ===
@dp.message(Form.resume_upload, F.document)
async def process_resume_file(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await message.answer(texts[lang]['analyzing'])
    
    file_id = message.document.file_id
    file_info = await bot.get_file(file_id)
    file_bytes_io = await bot.download_file(file_info.file_path)
    
    user_data = await state.get_data()
    gemini_summary = ""

    try:
        # PDF va DOCX tahlili
        if message.document.mime_type == "application/pdf":
            pdf_part = {"mime_type": "application/pdf", "data": file_bytes_io.read()}
            prompt = texts[lang]['gemini_file_prompt']
            response = await model.generate_content_async([prompt, pdf_part])
            gemini_summary = response.text
        else: # DOCX
            document = docx.Document(file_bytes_io)
            resume_text = "\n".join(
                cell.text for table in document.tables for row in table.rows for cell in row.cells
            ) + "\n" + "\n".join(para.text for para in document.paragraphs)

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
@dp.message(Form.convo_experience)
async def process_convo_experience(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(experience=message.text)
    await message.answer(texts[lang]['ask_skills_convo'])
    await state.set_state(Form.convo_skills)

@dp.message(Form.convo_skills)
async def process_convo_skills(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(skills=message.text)
    await message.answer(texts[lang]['ask_contact_convo'])
    await state.set_state(Form.convo_contact)

@dp.message(Form.convo_contact)
async def process_convo_contact(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(contact=message.text)
    await message.answer(texts[lang]['analyzing'])

    user_data = await state.get_data()
    
    convo_data_text = (
        f"Tajribasi: {user_data.get('experience')}\n"
        f"Ko'nikmalari: {user_data.get('skills')}\n"
        f"Aloqa: {user_data.get('contact')}"
    )
    prompt = texts[lang]['gemini_convo_prompt'].format(resume_text=convo_data_text)
    response = await model.generate_content_async(prompt)
    gemini_summary = response.text
    
    hr_notification_template = texts[lang]['hr_notification_convo']
    hr_summary_text = hr_notification_template.format(
        name=user_data.get('name'),
        experience=user_data.get('experience'),
        skills=user_data.get('skills'),
        contact=user_data.get('contact'),
        summary=gemini_summary
    )

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