# main.py fayli (Тилни сақлайдиган якуний версия)

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
)

# Boshqa modullarni import qilish
from savol_javob import router as faq_router
from ariza_topshirish import router as application_router
from admin_panel import router as admin_router
import database as db
from keyboards import texts, get_user_keyboard, get_admin_keyboard
from states import MainForm, FaqForm, AppForm, AdminForm

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

# ASOSIY HANDLER'LAR

@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    db.add_user(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username
    )
    language_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")]
    ])
    await message.answer(
        texts['uz']['welcome_lang'] + "\n\n" + texts['ru']['welcome_lang'],
        reply_markup=language_keyboard
    )
    await state.set_state(MainForm.language_selection)


@dp.callback_query(MainForm.language_selection, F.data.startswith('lang_'))
async def process_language_selection(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split('_')[1]
    await state.update_data(language=lang)
    await callback.message.delete()

    user_id = str(callback.from_user.id)
    
    if user_id == ADMIN_ID:
        keyboard = get_admin_keyboard(lang)
    else:
        keyboard = get_user_keyboard(lang)
    
    await callback.message.answer(texts[lang]['welcome_menu'], reply_markup=keyboard)
    
    await state.set_state(MainForm.main_menu)
    await callback.answer()


@dp.message(F.text.in_([texts['uz']['apply_button'], texts['ru']['apply_button']]))
async def handle_apply_button(message: Message, state: FSMContext):
    lang = await get_user_lang(state)
    # --- МУҲИМ ТУЗАТИШ: state.clear() олиб ташланди ---
    # Энди ҳолат тўғридан-тўғри ўзгартирилади ва тил маълумоти сақланиб қолади
    await message.answer(texts[lang]['ask_name'])
    await state.set_state(AppForm.name)


@dp.message(F.text.in_([texts['uz']['faq_button'], texts['ru']['faq_button']]))
async def handle_faq_button(message: Message, state: FSMContext):
    lang = await get_user_lang(state)
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts[lang]['button_share_contact'], request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer(texts[lang]['faq_auth_prompt'], reply_markup=contact_keyboard)
    await state.set_state(FaqForm.verification)


@dp.message(F.text.in_([texts['uz']['broadcast_button'], texts['ru']['broadcast_button']]))
async def handle_broadcast_button(message: Message, state: FSMContext):
    if str(message.from_user.id) == ADMIN_ID:
        lang = await get_user_lang(state)
        await message.answer(texts[lang]['ask_announcement'], reply_markup=ReplyKeyboardRemove())
        await state.set_state(AdminForm.waiting_for_announcement)


async def main():
    db.init_db()
    dp.include_router(admin_router)
    dp.include_router(application_router)
    dp.include_router(faq_router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
