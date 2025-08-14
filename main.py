import asyncio
import logging
import io
import docx # Yangi import
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import BOT_TOKEN, GEMINI_API_KEY
import os
from dotenv import load_dotenv

load_dotenv()

# --- SOZLAMALAR ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- TILLAR UCHUN LUG'AT ---
texts = {
    'uz': {
        'welcome': "Assalomu alaykum! Tilni tanlang.",
        'ask_name': "To'liq ism-familiyangizni kiriting:",
        'ask_experience': "Rahmat! Endi tajribangiz haqida yozing (masalan, '2 yil SMM sohasida').",
        'ask_portfolio': "Ajoyib! Endi rezyumeingizni PDF yoki DOCX formatida yuboring.",
        'analyzing': "Ma'lumotlar qabul qilindi. Hozir sun'iy intellekt yordamida tahlil qilinmoqda, bir oz kuting...",
        'summary_title': "**Sun'iy intellekt xulosasi:**\n\n",
        'goodbye': "\n\nRahmat! Tez orada siz bilan bog'lanamiz. ✅",
        'file_error': "Iltimos, rezyumeni faqat PDF yoki DOCX formatida yuboring.",
        'gemini_file_prompt': """Sen tajribali HR-menejersan. Ilova qilingan fayl nomzodning rezyumesi hisoblanadi. 
        Ushbu rezyumeni o'qib chiqib, nomzod haqida o'zbek tilida qisqacha va aniq xulosa yoz.
        Tahlil quyidagi formatda bo'lsin:
        Umumiy xulosa: [Nomzodning tajribasi, ko'nikmalari va ma'lumotlari asosida 2-3 gaplik xulosa]
        Kuchli tomonlari: [Rezyumedan topilgan eng asosiy 2-3 ta kuchli jihat]
        Dastlabki baho: [Mos keladi / O'ylab ko'rish kerak / Tajribasi kam]""",
        'gemini_text_prompt': """Sen tajribali HR-menejersan. Quyida nomzodning rezyumesidan olingan matn keltirilgan. 
        Ushbu matnni tahlil qilib, nomzod haqida o'zbek tilida qisqacha va aniq xulosa yoz.
        Tahlil quyidagi formatda bo'lsin:
        Umumiy xulosa: [Nomzodning tajribasi, ko'nikmalari va ma'lumotlari asosida 2-3 gaplik xulosa]
        Kuchli tomonlari: [Rezyumedan topilgan eng asosiy 2-3 ta kuchli jihat]
        Dastlabki baho: [Mos keladi / O'ylab ko'rish kerak / Tajribasi kam]
        
        Rezyume matni:
        {resume_text}
        """
    },
    'ru': {
        # Rus tilidagi tarjimalar ham xuddi shunday yangilanishi mumkin
        # Hozircha o'zgarishsiz qoldiramiz
        'welcome': "Здравствуйте! Выберите язык.",
        'ask_name': "Введите ваше полное имя и фамилию:",
        'ask_experience': "Спасибо! Теперь опишите ваш опыт (например, '2 года в сфере SMM').",
        'ask_portfolio': "Отлично! Теперь отправьте ваше резюме в формате PDF или DOCX.",
        'analyzing': "Данные получены. Сейчас они анализируются с помощью искусственного интеллекта, подождите немного...",
        'summary_title': "**Заключение искусственного интеллекта:**\n\n",
        'goodbye': "\n\nСпасибо! Мы скоро с вами свяжемся. ✅",
        'file_error': "Пожалуйста, отправьте резюме только в формате PDF или DOCX.",
        'gemini_file_prompt': """Ты опытный HR-менеджер. Приложенный PDF-файл является резюме кандидата. 
        Прочитай это резюме и напиши краткое и четкое заключение о кандидате на русском языке.
        Анализ должен быть в следующем формате:
        Общее заключение: [Заключение из 2-3 предложений на основе опыта, навыков и образования кандидата]
        Сильные стороны: [2-3 ключевые сильные стороны, найденные в резюме]
        Предварительная оценка: [Подходит / Стоит рассмотреть / Недостаточно опыта]""",
        'gemini_text_prompt': """Ты опытный HR-менеджер. Ниже приведен текст из резюме кандидата. 
        Проанализируй этот текст и напиши краткое и четкое заключение о кандидате на русском языке.
        Анализ должен быть в следующем формате:
        Общее заключение: [Заключение из 2-3 предложений на основе опыта, навыков и образования кандидата]
        Сильные стороны: [2-3 ключевые сильные стороны, найденные в резюме]
        Предварительная оценка: [Подходит / Стоит рассмотреть / Недостаточно опыта]
        
        Текст резюме:
        {resume_text}
        """
    }
}


# --- BOTNING XOTIRASI (FSM) ---
class Form(StatesGroup):
    language_selection = State()
    name = State()
    experience = State()
    resume_file = State()

# --- ASOSIY BOT QISMI ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
language_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")], [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")]])

async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')

# --- BOT SUHBATLOGIKASI ---
# /start, til tanlash, ism, tajriba handler'lari o'zgarishsiz qoladi

@dp.message(Command("start"))
async def send_welcome(message: types.Message, state: FSMContext):
    await message.reply(f"{texts['uz']['welcome']}\n{texts['ru']['welcome']}", reply_markup=language_keyboard)
    await state.set_state(Form.language_selection)

@dp.callback_query(Form.language_selection, F.data.startswith('lang_'))
async def process_language_selection(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split('_')[1]
    await state.update_data(language=lang)
    await callback.message.edit_reply_markup()
    await callback.message.answer(texts[lang]['ask_name'])
    await state.set_state(Form.name)
    await callback.answer()

@dp.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(name=message.text)
    await message.answer(texts[lang]['ask_experience'])
    await state.set_state(Form.experience)

@dp.message(Form.experience)
async def process_experience(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(experience=message.text)
    await message.answer(texts[lang]['ask_portfolio'])
    await state.set_state(Form.resume_file)

# PDF YOKI DOCX FAYLLARNI QABUL QILADIGAN YANGI HANDLER
@dp.message(Form.resume_file, F.document)
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
    
    gemini_summary = ""
    try:
        if file_mime_type == "application/pdf":
            # PDF faylni to'g'ridan-to'g'ri yuborish
            pdf_part = {"mime_type": "application/pdf", "data": file_bytes_io.read()}
            prompt = texts[lang]['gemini_file_prompt']
            response = await model.generate_content_async([prompt, pdf_part])
            gemini_summary = response.text

        elif file_mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            # DOCX fayldan matnni ajratib olish
            document = docx.Document(file_bytes_io)
            resume_text = "\n".join([para.text for para in document.paragraphs])
            
            # Ajratib olingan matnni tahlilga yuborish
            prompt = texts[lang]['gemini_text_prompt'].format(resume_text=resume_text)
            response = await model.generate_content_async(prompt)
            gemini_summary = response.text

    except Exception as e:
        logging.error(f"Faylni tahlil qilishdagi xato: {e}")
        gemini_summary = "Faylni tahlil qilishda xatolik yuz berdi."

    logging.info(f"--- GEMINI FAYL XULOSASI ({lang.upper()}) ---\n{gemini_summary}\n-----------------------")
    await message.answer(f"{texts[lang]['summary_title']}{gemini_summary}{texts[lang]['goodbye']}")
    await state.clear()

# Agar foydalanuvchi fayl o'rniga boshqa narsa yuborsa
@dp.message(Form.resume_file)
async def process_resume_invalid(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await message.reply(texts[lang]['file_error'])

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())