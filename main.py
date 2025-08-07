import asyncio
import logging
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import BOT_TOKEN, GEMINI_API_KEY

# --- SOZLAMALAR ---
# Konsolga botning ishlashi haqida ma'lumot chiqarish uchun sozlash
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Gemini modelini sozlash
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- BOTNING XOTIRASI (FSM) ---
class Form(StatesGroup):
    name = State()
    experience = State()
    portfolio = State()

# --- ASOSIY BOT QISMI ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Gemini bilan tahlil qiluvchi funksiya
async def analyze_with_gemini(data: dict):
    prompt = f"""
    Sen tajribali HR-menejersan. Quyidagi nomzodning ma'lumotlarini tahlil qilib, u haqida qisqacha va aniq xulosa yoz.

    Nomzod ma'lumotlari:
    - Ism: {data.get('name')}
    - Tajribasi: {data.get('experience')}

    Xulosa quyidagi formatda bo'lsin:
    Xulosa: [Nomzodning tajribasi va so'zlari asosida 2-3 gaplik xulosa]
    Dastlabki baho: [Mos keladi / O'ylab ko'rish kerak / Tajribasi kam]
    """
    try:
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        logging.error(f"Gemini API xatosi: {e}")
        return "Sun'iy intellekt bilan tahlil qilishda xatolik yuz berdi."

# --- BOT SUHBATLOGIKASI ---
@dp.message(Command("start"))
async def send_welcome(message: types.Message, state: FSMContext):
    await message.reply("Assalomu alaykum! Nomzod anketasini to'ldirishni boshlaymiz.\n\nTo'liq ism-familiyangizni kiriting:")
    await state.set_state(Form.name)

@dp.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Rahmat! Endi tajribangiz haqida yozing (masalan, '2 yil SMM sohasida').")
    await state.set_state(Form.experience)

@dp.message(Form.experience)
async def process_experience(message: types.Message, state: FSMContext):
    await state.update_data(experience=message.text)
    await message.answer("Ajoyib! Endi portfoliongizni yuboring (fayl yoki havolasini).")
    await state.set_state(Form.portfolio)

@dp.message(Form.portfolio)
async def process_portfolio(message: types.Message, state: FSMContext):
    await message.answer("Ma'lumotlar qabul qilindi. Hozir sun'iy intellekt yordamida tahlil qilinmoqda, bir oz kuting...")
    
    user_data = await state.get_data()
    
    # === GEMINI'NI ISHGA SOLAMIZ! ===
    gemini_summary = await analyze_with_gemini(user_data)
    
    # Natijani terminalga va foydalanuvchiga ko'rsatamiz
    logging.info(f"--- GEMINI XULOSASI ---\n{gemini_summary}\n-----------------------")
    await message.answer(f"**Sun'iy intellekt xulosasi:**\n\n{gemini_summary}\n\nRahmat! Tez orada siz bilan bog'lanamiz. ✅")
    
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())