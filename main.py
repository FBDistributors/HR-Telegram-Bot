# main.py fayli (Tozalangan va to'g'ri ishlaydigan versiya)

import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, Message,
    CallbackQuery, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton,
    BotCommandScopeDefault
)

# Boshqa modullarni import qilish
from savol_javob import router as faq_router
from ariza_topshirish import router as application_router
from admin_panel import router as admin_router
from suggestion_complaint import router as suggestion_router
from documents import router as documents_router
import database as db
from keyboards import texts, get_user_keyboard, get_admin_main_keyboard
from states import MainForm, FaqForm, AppForm, AdminForm, DocumentForm
from scheduler import check_unanswered_questions, cleanup_expired_documents
from utils.commands import user_commands

# SOZLAMALAR
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ASOSIY BOT QISMI
if not BOT_TOKEN:
    logging.critical("Bot tokeni topilmadi! Dastur to'xtatildi.")
    exit()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')


async def set_bot_commands(bot_instance: Bot):
    """Bot uchun menyu buyruqlarini o'rnatadi"""
    await bot_instance.set_my_commands(user_commands, BotCommandScopeDefault())
    logging.info("Bot uchun standart buyruqlar o'rnatildi.")


# --- ASOSIY HANDLER'LAR ---

@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    await db.add_user(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username
    )
    
    caption_text = (
        "Assalomu alaykum! Muloqot uchun qulay tilni tanlang.\n\n"
        "Здравствуйте! Пожалуйста, выберите удобный язык для общения."
    )
    
    language_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")]
    ])
    
    await message.answer(
        text=caption_text,
        reply_markup=language_keyboard,
        parse_mode="HTML"
    )
    
    await state.set_state(MainForm.language_selection)


@dp.callback_query(MainForm.language_selection, F.data.startswith('lang_'))
async def process_language_selection(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split('_')[1]
    await state.update_data(language=lang)
    await callback.message.delete()

    user_id = str(callback.from_user.id)
    
    if user_id == ADMIN_ID:
        keyboard = get_admin_main_keyboard(lang)
    else:
        keyboard = get_user_keyboard(lang)
    
    await callback.message.answer(texts[lang]['welcome_menu'], reply_markup=keyboard)
    
    await state.set_state(MainForm.main_menu)
    await callback.answer()


@dp.message(F.text.in_([texts['uz']['apply_button'], texts['ru']['apply_button']]))
async def handle_apply_button(message: Message, state: FSMContext):
    lang = await get_user_lang(state)
    await message.answer(texts[lang]['ask_name'])
    await state.set_state(AppForm.name)


async def handle_faq_button_logic(message: Message, state: FSMContext):
    """Telefon raqam so'rash mantig'ini o'zida saqlaydigan yordamchi funksiya"""
    lang = await get_user_lang(state)
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts[lang]['button_share_contact'], request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer(texts[lang]['faq_auth_prompt'], reply_markup=contact_keyboard)
    await state.set_state(FaqForm.verification)


@dp.message(F.text.in_([texts['uz']['faq_button'], texts['ru']['faq_button']]))
async def handle_faq_shortcut(message: Message, state: FSMContext):
    """
    Agar foydalanuvchi allaqachon xodim sifatida tanilgan bo'lsa, uni to'g'ridan-to'g'ri
    FAQ bo'limiga o'tkazadi. Aks holda, raqam so'raydi.
    """
    lang = await get_user_lang(state)
    user_id = message.from_user.id

    if await db.is_employee_by_tg_id(user_id):
        logging.info(f"Xodim {user_id} FAQ bo'limiga qayta kirdi.")
        
        if str(user_id) == ADMIN_ID:
            keyboard = get_admin_main_keyboard(lang)
        else:
            keyboard = get_user_keyboard(lang)
        
        await message.answer(texts[lang]['faq_welcome'], reply_markup=keyboard)
        await state.set_state(FaqForm.in_process)
    else:
        # Agar tanilmagan bo'lsa, telefon raqam so'raymiz
        await handle_faq_button_logic(message, state)


# Asosiy ishga tushirish funksiyasi
async def main():
    await db.init_db()
    
    await set_bot_commands(bot)

    # Polling boshlashdan oldin webhookni olib tashlaymiz
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("Telegram webhook o'chirildi (drop_pending_updates=True).")
    except Exception as exc:
        logging.warning(f"Webhook o'chirishda ogohlantirish: {exc}")

    dp.include_router(suggestion_router)
    dp.include_router(documents_router)
    dp.include_router(admin_router)
    dp.include_router(application_router)
    dp.include_router(faq_router)
    asyncio.create_task(check_unanswered_questions(bot))
    asyncio.create_task(cleanup_expired_documents())
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Windows uchun SelectorEventLoop ishlatish (psycopg3 talabi)
    import sys
    if sys.platform == 'win32':
        import selectors
        selector = selectors.SelectSelector()
        loop = asyncio.SelectorEventLoop(selector)
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    else:
        asyncio.run(main())

