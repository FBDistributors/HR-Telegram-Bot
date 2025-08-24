# main.py fayli (Yakuniy Boshqaruv Markazi)

import asyncio
import logging
import os
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

# --- DIAGNOSTIKA QISMINI IZOHGA OLAMIZ (ENDI KERAK EMAS) ---
# print("--- .env faylini tekshirish ---")
# api_key = os.getenv("GEMINI_API_KEY")
# bot_token_check = os.getenv("BOT_TOKEN")
# print(f"O'qilgan GEMINI_API_KEY: {api_key}")
# print(f"O'qilgan BOT_TOKEN: {bot_token_check}")
# print("-----------------------------")
# --- DIAGNOSTIKA TUGADI ---


from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

# Boshqa fayllardagi router'lar va FSM'larni import qilish
from savol_javob import router as faq_router, FaqForm
from ariza_topshirish import router as application_router, AppForm


# --- SOZLAMALAR ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- TILLAR UCHUN LUG'AT (FAQAT ASOSIY MENYU UCHUN) ---
texts = {
    'uz': {
        'welcome_lang': "Assalomu alaykum! Muloqot uchun qulay tilni tanlang.",
        'welcome_menu': "Kerakli bo'limni tanlang:",
        'main_menu_button': "🏠 Bosh menyu",
        'main_menu_info': "Suhbatni istalgan paytda boshidan boshlash uchun 'Bosh menyu' tugmasidan foydalaning.",
        'main_menu_apply': "📝 Ariza topshirish",
        'main_menu_faq': "❓ Savol berish (FAQ)",
        'hide_menu_text': "Doimiy tugmalar yopildi. Qaytadan chiqarish uchun /start buyrug'ini bering.",
        'button_share_contact': "📱 Kontaktimni ulashish",
        'faq_auth_prompt': "Bu bo'lim faqat kompaniya xodimlari uchun. Iltimos, shaxsingizni tasdiqlash uchun kontaktingizni yuboring.",
        # --- MUHIM TUZATISH: 'ask_name' MATNINI SHU YERGA QO'SHAMIZ ---
        'ask_name': "To'liq ism-sharifingizni kiriting (masalan, Olimov Salim).",
    },
    'ru': {
        'welcome_lang': "Здравствуйте! Пожалуйста, выберите удобный язык для общения.",
        'welcome_menu': "Пожалуйста, выберите нужный раздел:",
        'main_menu_button': "🏠 Главное меню",
        'main_menu_info': "Используйте кнопку 'Главное меню', чтобы начать разговор заново в любой момент.",
        'main_menu_apply': "📝 Подать заявку",
        'main_menu_faq': "❓ Задать вопрос (FAQ)",
        'hide_menu_text': "Постоянные кнопки скрыты. Чтобы показать их снова, отправьте команду /start.",
        'button_share_contact': "📱 Поделиться моим контактом",
        'faq_auth_prompt': "Этот раздел предназначен только для сотрудников компании. Пожалуйста, отправьте свой контакт для подтверждения личности.",
        # --- MUHIM TUZATISH: 'ask_name' MATNINI RUSCHA VARIANTIGA HAM QO'SHAMIZ ---
        'ask_name': "Введите Ваши полные имя и фамилию (например, Салимов Олим).",
    }
}

# --- BOTNING ASOSIY HOLATLARI (FSM) ---
class Form(StatesGroup):
    language_selection = State()
    main_menu = State()

# --- ASOSIY BOT QISMI ---
if not BOT_TOKEN:
    logging.critical("Bot tokeni topilmadi! Dastur to'xtatildi.")
    exit()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')

# --- ASOSIY BOT HANDLER'LARI ---
@dp.message(CommandStart())
async def send_welcome(message: Message, state: FSMContext):
    await state.clear()
    language_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")]
    ])
    await message.reply(texts['uz']['welcome_lang'] + "\n\n" + texts['ru']['welcome_lang'], reply_markup=language_keyboard)
    await state.set_state(Form.language_selection)

@dp.message(F.text.in_([texts['uz']['main_menu_button'], texts['ru']['main_menu_button']]))
async def handle_main_menu_button(message: Message, state: FSMContext):
    await send_welcome(message, state)

@dp.callback_query(Form.language_selection, F.data.startswith('lang_'))
async def process_language_selection(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split('_')[1]
    await state.update_data(language=lang)
    
    await callback.message.delete()
    
    main_menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts[lang]['main_menu_apply'], callback_data="menu_apply")],
        [InlineKeyboardButton(text=texts[lang]['main_menu_faq'], callback_data="menu_faq")]
    ])
    
    persistent_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts[lang]['main_menu_button'])]],
        resize_keyboard=True
    )
    await callback.message.answer(texts[lang]['welcome_menu'], reply_markup=main_menu_keyboard)
    await callback.message.answer(texts[lang]['main_menu_info'], reply_markup=persistent_keyboard)
    
    await state.set_state(Form.main_menu)
    await callback.answer()

@dp.callback_query(Form.main_menu, F.data.startswith('menu_'))
async def process_main_menu_choice(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.split('_')[1]
    lang = await get_user_lang(state)
    
    try:
        await callback.message.delete_reply_markup()
    except TelegramBadRequest:
        logging.info("Xabarni o'zgartirib bo'lmadi.")

    if choice == "apply":
        # Endi bu qator xatosiz ishlaydi, chunki 'ask_name' shu faylda mavjud
        await callback.message.answer(texts[lang]['ask_name'])
        await state.set_state(AppForm.name) 
    elif choice == "faq":
        contact_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=texts[lang]['button_share_contact'], request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await callback.message.answer(texts[lang]['faq_auth_prompt'], reply_markup=contact_keyboard)
        await state.set_state(FaqForm.verification)
    
    await callback.answer()

@dp.message(Command("hidemenu"))
async def hide_menu(message: Message, state: FSMContext):
    lang = await get_user_lang(state)
    await message.answer(texts[lang]['hide_menu_text'], reply_markup=ReplyKeyboardRemove())

async def main():
    dp.include_router(application_router)
    dp.include_router(faq_router)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
