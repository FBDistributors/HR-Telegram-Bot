import asyncio
import logging
import io
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
# main.py faylining boshidagi import qismini o'zgartiring
import os
from dotenv import load_dotenv

load_dotenv() # .env faylidagi o'zgaruvchilarni yuklaydi

# ... boshqa importlar (aiogram, genai, va hokazo)

# --- SOZLAMALAR ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Qolgan kodlar o'zgarishsiz qoladi...

# --- SOZLAMALAR ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- TILLAR UCHUN LUG'AT (o'zgarishsiz qoladi) ---
texts = {
    'uz': {
        'welcome': "Assalomu alaykum! Tilni tanlang.",
        'ask_name': "To'liq ism-familiyangizni kiriting:",
        'ask_experience': "Rahmat! Endi tajribangiz haqida yozing (masalan, '2 yil SMM sohasida').",
        'ask_portfolio': "Ajoyib! Endi portfoliongizni yoki rezyumeingizni PDF formatida yuboring.",
        'analyzing': "Ma'lumotlar qabul qilindi. Hozir sun'iy intellekt yordamida tahlil qilinmoqda, bir oz kuting...",
        'summary_title': "**Sun'iy intellekt xulosasi:**\n\n",
        'goodbye': "\n\nRahmat! Tez orada siz bilan bog'lanamiz. ✅",
        'gemini_pdf_prompt': """Sen tajribali HR-menejersan. Ilova qilingan PDF fayl nomzodning rezyumesi hisoblanadi. 
        Ushbu rezyumeni o'qib chiqib, nomzod haqida o'zbek tilida qisqacha va aniq xulosa yoz.

        Tahlil quyidagi formatda bo'lsin:
        Umumiy xulosa: [Nomzodning tajribasi, ko'nikmalari va ma'lumotlari asosida 2-3 gaplik xulosa]
        Kuchli tomonlari: [Rezyumedan topilgan eng asosiy 2-3 ta kuchli jihat]
        Dastlabki baho: [Mos keladi / O'ylab ko'rish kerak / Tajribasi kam]"""
    },
    'ru': {
        'welcome': "Здравствуйте! Выберите язык.",
        'ask_name': "Введите ваше полное имя и фамилию:",
        'ask_experience': "Спасибо! Теперь опишите ваш опыт (например, '2 года в сфере SMM').",
        'ask_portfolio': "Отлично! Теперь отправьте ваше портфолио или резюме в формате PDF.",
        'analyzing': "Данные получены. Сейчас они анализируются с помощью искусственного интеллекта, подождите немного...",
        'summary_title': "**Заключение искусственного интеллекта:**\n\n",
        'goodbye': "\n\nСпасибо! Мы скоро с вами свяжемся. ✅",
        'gemini_pdf_prompt': """Ты опытный HR-менеджер. Приложенный PDF-файл является резюме кандидата. 
        Прочитай это резюме и напиши краткое и четкое заключение о кандидате на русском языке.

        Анализ должен быть в следующем формате:
        Общее заключение: [Заключение из 2-3 предложений на основе опыта, навыков и образования кандидата]
        Сильные стороны: [2-3 ключевые сильные стороны, найденные в резюме]
        Предварительная оценка: [Подходит / Стоит рассмотреть / Недостаточно опыта]"""
    }
}


# --- BOTNING XOTIRASI (FSM) ---
class Form(StatesGroup):
    language_selection = State()
    name = State()
    experience = State()
    portfolio_pdf = State() # Holat nomini o'zgartirdik

# --- ASOSIY BOT QISMI ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

language_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")],
    [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")]
])

# --- BOT SUHBATLOGIKASI ---
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

async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')

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
    await state.set_state(Form.portfolio_pdf)

# FAQAT PDF FAYLLARNI QABUL QILADIGAN YANGI HANDLER
@dp.message(Form.portfolio_pdf, F.document.mime_type == "application/pdf")
async def process_pdf_resume(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await message.answer(texts[lang]['analyzing'])
    
    # PDF faylni Telegramdan yuklab olish
    file_id = message.document.file_id
    file_info = await bot.get_file(file_id)
    file_bytes = await bot.download_file(file_info.file_path)

    prompt = texts[lang]['gemini_pdf_prompt']
    
    try:
        # Faylni alohida yuklamasdan, to'g'ridan-to'g'ri modelga yuborish
        pdf_part = {
            "mime_type": "application/pdf",
            "data": file_bytes.read() # .read() ni qo'shdik
        }
        
        # Modelga matn (prompt) va faylni (pdf_part) birgalikda yuborish
        response = await model.generate_content_async([prompt, pdf_part])
        gemini_summary = response.text

    except Exception as e:
        logging.error(f"Gemini API xatosi: {e}")
        gemini_summary = "PDF faylni tahlil qilishda xatolik yuz berdi."

    logging.info(f"--- GEMINI PDF XULOSASI ({lang.upper()}) ---\n{gemini_summary}\n-----------------------")
    await message.answer(f"{texts[lang]['summary_title']}{gemini_summary}{texts[lang]['goodbye']}")
    
    await state.clear()
    
# Agar foydalanuvchi PDF o'rniga boshqa narsa yuborsa
@dp.message(Form.portfolio_pdf)
async def process_pdf_invalid(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await message.reply("Iltimos, rezyumeni faqat PDF formatida yuboring.")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())