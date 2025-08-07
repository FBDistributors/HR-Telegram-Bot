import asyncio
import logging
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import BOT_TOKEN, GEMINI_API_KEY

# --- SOZLAMALAR ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- TILLAR UCHUN LUG'AT ---
texts = {
    'uz': {
        'welcome': "Assalomu alaykum! Tilni tanlang.",
        'ask_name': "To'liq ism-familiyangizni kiriting:",
        'ask_experience': "Rahmat! Endi tajribangiz haqida yozing (masalan, '2 yil SMM sohasida').",
        'ask_portfolio': "Ajoyib! Endi portfoliongizni yuboring (fayl yoki havolasini).",
        'analyzing': "Ma'lumotlar qabul qilindi. Hozir sun'iy intellekt yordamida tahlil qilinmoqda, bir oz kuting...",
        'summary_title': "**Sun'iy intellekt xulosasi:**\n\n",
        'goodbye': "\n\nRahmat! Tez orada siz bilan bog'lanamiz. ✅",
        'gemini_prompt': """Sen tajribali HR-menejersan. Quyidagi nomzodning ma'lumotlarini tahlil qilib, u haqida o'zbek tilida qisqacha va aniq xulosa yoz.
        Nomzod ma'lumotlari:
        - Ism: {name}
        - Tajribasi: {experience}
        Xulosa quyidagi formatda bo'lsin:
        Xulosa: [Nomzodning tajribasi va so'zlari asosida 2-3 gaplik xulosa]
        Dastlabki baho: [Mos keladi / O'ylab ko'rish kerak / Tajribasi kam]"""
    },
    'ru': {
        'welcome': "Здравствуйте! Выберите язык.",
        'ask_name': "Введите ваше полное имя и фамилию:",
        'ask_experience': "Спасибо! Теперь опишите ваш опыт (например, '2 года в сфере SMM').",
        'ask_portfolio': "Отлично! Теперь отправьте ваше портфолио (файлом или ссылкой).",
        'analyzing': "Данные получены. Сейчас они анализируются с помощью искусственного интеллекта, подождите немного...",
        'summary_title': "**Заключение искусственного интеллекта:**\n\n",
        'goodbye': "\n\nСпасибо! Мы скоро с вами свяжемся. ✅",
        'gemini_prompt': """Ты опытный HR-менеджер. Проанализируй данные кандидата и напиши краткое и четкое заключение о нём на русском языке.
        Данные кандидата:
        - Имя: {name}
        - Опыт: {experience}
        Заключение должно быть в следующем формате:
        Заключение: [Заключение из 2-3 предложений на основе опыта и слов кандидата]
        Предварительная оценка: [Подходит / Стоит рассмотреть / Недостаточно опыта]"""
    }
}

# --- BOTNING XOTIRASI (FSM) ---
class Form(StatesGroup):
    language_selection = State()
    name = State()
    experience = State()
    portfolio = State()

# --- ASOSIY BOT QISMI ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Til tanlash uchun tugmalar
language_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")],
    [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")]
])

# --- BOT SUHBATLOGIKASI ---
@dp.message(Command("start"))
async def send_welcome(message: types.Message, state: FSMContext):
    await message.reply(f"{texts['uz']['welcome']}\n{texts['ru']['welcome']}", reply_markup=language_keyboard)
    await state.set_state(Form.language_selection)

# Til tanlash tugmasi bosilganda ishlaydigan handler
@dp.callback_query(Form.language_selection, F.data.startswith('lang_'))
async def process_language_selection(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split('_')[1]  # 'uz' yoki 'ru'
    await state.update_data(language=lang)
    
    await callback.message.edit_reply_markup() # Tugmalarni o'chirish
    await callback.message.answer(texts[lang]['ask_name'])
    await state.set_state(Form.name)
    await callback.answer()

async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz') # Agar til topilmasa, standart 'uz'

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
    await state.set_state(Form.portfolio)

@dp.message(Form.portfolio)
async def process_portfolio(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await message.answer(texts[lang]['analyzing'])
    
    user_data = await state.get_data()
    
    # Gemini'ga yuboriladigan promptni tanlangan tilga moslash
    prompt = texts[lang]['gemini_prompt'].format(
        name=user_data.get('name'),
        experience=user_data.get('experience')
    )
    
    try:
        response = await model.generate_content_async(prompt)
        gemini_summary = response.text
    except Exception as e:
        logging.error(f"Gemini API xatosi: {e}")
        gemini_summary = "Sun'iy intellekt bilan tahlil qilishda xatolik yuz berdi."
    
    logging.info(f"--- GEMINI XULOSASI ({lang.upper()}) ---\n{gemini_summary}\n-----------------------")
    await message.answer(f"{texts[lang]['summary_title']}{gemini_summary}{texts[lang]['goodbye']}")
    
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())