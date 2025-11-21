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
from product_catalog import router as product_router
import database as db
from keyboards import texts, get_user_keyboard, get_admin_main_keyboard, get_external_user_keyboard, get_employee_keyboard
from states import MainForm, FaqForm, AppForm, AdminForm, DocumentForm
from scheduler import check_unanswered_questions, cleanup_expired_documents
from utils.commands import user_commands

# SOZLAMALAR
BOT_TOKEN = os.getenv("BOT_TOKEN")
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

    user_id = callback.from_user.id
    
    # Avval employees jadvalidan telegram_id bo'yicha tekshiramiz
    if await db.is_employee_by_tg_id(user_id):
        # Agar xodim topilsa, to'g'ridan-to'g'ri xodim sifatida tan olamiz
        await state.update_data(user_type='employee')
        await show_main_menu(callback.message, state, user_id, lang)
    else:
        # Agar topilmasa, xodim/xodim emas tanlashni so'raymiz
        user_type_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=texts[lang]['employee_button'], callback_data="user_type_employee")],
            [InlineKeyboardButton(text=texts[lang]['external_button'], callback_data="user_type_external")]
        ])
        
        await callback.message.answer(texts[lang]['ask_user_type'], reply_markup=user_type_keyboard)
        await state.set_state(MainForm.user_type_selection)
    
    await callback.answer()


@dp.callback_query(MainForm.user_type_selection, F.data.startswith('user_type_'))
async def process_user_type_selection(callback: CallbackQuery, state: FSMContext):
    user_type = callback.data.split('_')[2]  # 'employee' yoki 'external'
    lang = await get_user_lang(state)
    user_id = callback.from_user.id
    
    await callback.message.delete()
    
    if user_type == 'employee':
        # Xodim bo'lsa, xavfsizlik tekshiruvi
        # Avval telegram_id bo'yicha tekshiramiz
        if await db.is_employee_by_tg_id(user_id):
            # Topildi, keyboard ko'rsatamiz
            await state.update_data(user_type='employee')
            await show_main_menu(callback.message, state, user_id, lang)
        else:
            # Topilmadi, admin'ga so'rov yuborish yoki telefon raqam so'rash
            request_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=texts[lang]['send_request_to_admin_button'], callback_data="send_admin_request")],
                [InlineKeyboardButton(text=texts[lang]['skip_request_button'], callback_data="skip_admin_request")]
            ])
            await callback.message.answer(texts[lang]['employee_not_found'], reply_markup=request_keyboard)
            await state.set_state(MainForm.employee_verification)
    else:
        # Tashqi shaxs bo'lsa, kontakt so'raymiz (majburiy)
        await state.update_data(user_type='external')
        contact_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=texts[lang]['button_share_contact'], request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await callback.message.answer(texts[lang]['external_contact_prompt'], reply_markup=contact_keyboard)
        await state.set_state(MainForm.external_contact)
    
    await callback.answer()


@dp.callback_query(MainForm.employee_verification, F.data.in_(['send_admin_request', 'skip_admin_request']))
async def handle_admin_request_choice(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Admin'ga so'rov yuborish yoki o'tkazib yuborish"""
    lang = await get_user_lang(state)
    user_id = callback.from_user.id
    action = callback.data
    
    await callback.message.delete()
    
    if action == 'send_admin_request':
        # Admin'ga so'rov yuborish
        full_name = callback.from_user.full_name
        username = callback.from_user.username
        
        # Telefon raqamni bazadan olish
        phone_number = None
        try:
            from sqlalchemy import select
            from database import User, async_session_maker
            
            async with async_session_maker() as session:
                result = await session.execute(select(User).filter(User.user_id == user_id))
                user = result.scalars().first()
                if user and user.phone_number:
                    phone_number = user.phone_number
        except Exception as e:
            logging.error(f"Telefon raqamni olishda xatolik: {e}")
        
        # Agar telefon raqam bo'lmasa, foydalanuvchidan so'ramiz
        if not phone_number:
            contact_keyboard = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=texts[lang]['button_share_contact'], request_contact=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            await callback.message.answer(
                "Iltimos, admin'ga so'rov yuborish uchun kontaktingizni yuboring:",
                reply_markup=contact_keyboard
            )
            await state.update_data(pending_admin_request=True)
            await state.set_state(MainForm.employee_verification)
            await callback.answer()
            return
        
        # Admin'ga so'rov yuborish (faqat bir kishiga)
        ADMIN_TELEGRAM_ID = 7428788767  # Admin Telegram ID
        
        admin_message = (
            f"🔔 **Yangi xodim so'rovi**\n\n"
            f"👤 **FIO:** {full_name}\n"
        )
        if username:
            admin_message += f"📱 **Username:** @{username}\n"
        admin_message += f"📞 **Telefon:** {phone_number}\n"
        admin_message += f"🆔 **Telegram ID:** {user_id}\n\n"
        admin_message += f"Bu foydalanuvchi o'zini kompaniya xodimi deb tanlagan, lekin employees jadvalida topilmadi."
        
        # Admin'ga tasdiqlash/rad etish tugmalari bilan yuborish
        try:
            approve_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_employee_{user_id}")],
                [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_employee_{user_id}")]
            ])
            await bot.send_message(
                chat_id=ADMIN_TELEGRAM_ID,
                text=admin_message,
                parse_mode="Markdown",
                reply_markup=approve_keyboard
            )
            await callback.message.answer(texts[lang]['request_sent_to_admin'])
        except Exception as e:
            logging.error(f"Admin {ADMIN_TELEGRAM_ID} ga so'rov yuborib bo'lmadi: {e}")
            await callback.message.answer("Kechirasiz, admin'ga so'rov yuborib bo'lmadi. Iltimos, qayta urinib ko'ring.")
        
        # Foydalanuvchini tashqi shaxs sifatida davom ettirish
        await state.update_data(user_type='external')
        await show_main_menu(callback.message, state, user_id, lang)
    else:
        # O'tkazib yuborish
        await callback.message.answer(texts[lang]['request_skipped'])
        # Foydalanuvchini tashqi shaxs sifatida davom ettirish
        await state.update_data(user_type='external')
        await show_main_menu(callback.message, state, user_id, lang)
    
    await callback.answer()


@dp.callback_query(F.data.startswith('approve_employee_'))
async def handle_approve_employee(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Admin xodimni tasdiqlash"""
    user_id = int(callback.data.split('_')[2])
    admin_id = callback.from_user.id
    
    # Admin ekanligini tekshirish
    if not await db.is_admin(admin_id):
        await callback.answer("Sizda bu amalni bajarish uchun ruxsat yo'q.", show_alert=True)
        return
    
    # Foydalanuvchi ma'lumotlarini olish
    try:
        from sqlalchemy import select
        from database import User, Employee, async_session_maker
        
        async with async_session_maker() as session:
            # User jadvalidan ma'lumot olish
            result = await session.execute(select(User).filter(User.user_id == user_id))
            user = result.scalars().first()
            
            if user:
                # Avval employees jadvalida mavjudligini tekshiramiz (telegram_id bo'yicha)
                employee_result = await session.execute(
                    select(Employee).filter(Employee.telegram_id == user_id)
                )
                existing_employee = employee_result.scalars().first()
                
                if existing_employee:
                    # Agar telegram_id bo'yicha mavjud bo'lsa, yangilaymiz
                    existing_employee.full_name = user.full_name
                    if user.phone_number:
                        existing_employee.phone_number = user.phone_number
                    if not existing_employee.position or existing_employee.position == "Kiritilmagan":
                        existing_employee.position = "Kiritilmagan"
                    await session.commit()
                    employee_name = existing_employee.full_name
                else:
                    # Agar telegram_id bo'yicha topilmasa, telefon raqam bo'yicha tekshiramiz
                    if user.phone_number:
                        phone_result = await session.execute(
                            select(Employee).filter(Employee.phone_number == user.phone_number)
                        )
                        existing_by_phone = phone_result.scalars().first()
                        
                        if existing_by_phone:
                            # Agar telefon raqam bo'yicha mavjud bo'lsa, telegram_id ni yangilaymiz
                            existing_by_phone.telegram_id = user_id
                            existing_by_phone.full_name = user.full_name
                            await session.commit()
                            employee_name = existing_by_phone.full_name
                        else:
                            # Hech qanday mavjud emas, yangi qo'shamiz
                            # Telefon raqam unique bo'lishi kerak, shuning uchun user_id bilan birga unique qilamiz
                            phone_for_db = user.phone_number if user.phone_number else f"no_phone_{user_id}"
                            new_employee = Employee(
                                full_name=user.full_name,
                                phone_number=phone_for_db,
                                telegram_id=user_id,
                                position="Kiritilmagan",
                                is_admin='false'
                            )
                            session.add(new_employee)
                            await session.commit()
                            employee_name = user.full_name
                    else:
                        # Telefon raqam ham yo'q, yangi qo'shamiz
                        # Telefon raqam unique bo'lishi kerak, shuning uchun user_id bilan birga unique qilamiz
                        phone_for_db = f"no_phone_{user_id}"
                        new_employee = Employee(
                            full_name=user.full_name,
                            phone_number=phone_for_db,
                            telegram_id=user_id,
                            position="Kiritilmagan",
                            is_admin='false'
                        )
                        session.add(new_employee)
                        await session.commit()
                        employee_name = user.full_name
                
                # Foydalanuvchiga xabar yuborish
                await bot.send_message(
                    chat_id=user_id,
                    text="✅ Tabriklaymiz! Sizning so'rovingiz tasdiqlandi. Endi siz kompaniya xodimi sifatida botdan foydalanishingiz mumkin."
                )
                
                await callback.message.edit_text(f"✅ Foydalanuvchi {employee_name} (ID: {user_id}) xodim sifatida tasdiqlandi.")
                await callback.answer("Foydalanuvchi tasdiqlandi!")
            else:
                await callback.answer("Foydalanuvchi topilmadi.", show_alert=True)
    except Exception as e:
        logging.error(f"Xodimni tasdiqlashda xatolik: {e}")
        await callback.answer("Xatolik yuz berdi.", show_alert=True)


@dp.callback_query(F.data.startswith('reject_employee_'))
async def handle_reject_employee(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Admin xodimni rad etish"""
    user_id = int(callback.data.split('_')[2])
    admin_id = callback.from_user.id
    
    # Admin ekanligini tekshirish
    if not await db.is_admin(admin_id):
        await callback.answer("Sizda bu amalni bajarish uchun ruxsat yo'q.", show_alert=True)
        return
    
    # Foydalanuvchiga xabar yuborish
    try:
        await bot.send_message(
            chat_id=user_id,
            text="❌ Kechirasiz, sizning so'rovingiz rad etildi. Agar bu xato bo'lsa, iltimos, admin bilan bog'laning."
        )
        await callback.message.edit_text(f"❌ Foydalanuvchi (ID: {user_id}) so'rovi rad etildi.")
        await callback.answer("So'rov rad etildi!")
    except Exception as e:
        logging.error(f"Xodimni rad etishda xatolik: {e}")
        await callback.answer("Xatolik yuz berdi.", show_alert=True)


@dp.message(MainForm.employee_verification, F.contact)
async def process_employee_verification(message: Message, state: FSMContext, bot: Bot):
    """Xodimlar uchun telefon raqam orqali xavfsizlik tekshiruvi yoki admin'ga so'rov yuborish"""
    lang = await get_user_lang(state)
    user_id = message.from_user.id
    phone_number = message.contact.phone_number
    
    # Telefon raqamni bazaga saqlash
    try:
        await db.update_user_phone_number(user_id, phone_number)
    except Exception:
        pass
    
    # Agar admin'ga so'rov yuborish kutilayotgan bo'lsa
    user_data = await state.get_data()
    if user_data.get('pending_admin_request'):
        # Admin'ga so'rov yuborish
        full_name = message.from_user.full_name
        username = message.from_user.username
        ADMIN_TELEGRAM_ID = 7428788767  # Admin Telegram ID
        
        admin_message = (
            f"🔔 **Yangi xodim so'rovi**\n\n"
            f"👤 **FIO:** {full_name}\n"
        )
        if username:
            admin_message += f"📱 **Username:** @{username}\n"
        admin_message += f"📞 **Telefon:** {phone_number}\n"
        admin_message += f"🆔 **Telegram ID:** {user_id}\n\n"
        admin_message += f"Bu foydalanuvchi o'zini kompaniya xodimi deb tanlagan, lekin employees jadvalida topilmadi."
        
        try:
            approve_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_employee_{user_id}")],
                [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_employee_{user_id}")]
            ])
            await bot.send_message(
                chat_id=ADMIN_TELEGRAM_ID,
                text=admin_message,
                parse_mode="Markdown",
                reply_markup=approve_keyboard
            )
            await message.answer(texts[lang]['request_sent_to_admin'], reply_markup=ReplyKeyboardRemove())
            await state.update_data(pending_admin_request=False, user_type='external')
            await show_main_menu(message, state, user_id, lang)
            return
        except Exception as e:
            logging.error(f"Admin {ADMIN_TELEGRAM_ID} ga so'rov yuborib bo'lmadi: {e}")
            await message.answer("Kechirasiz, admin'ga so'rov yuborib bo'lmadi. Iltimos, qayta urinib ko'ring.", reply_markup=ReplyKeyboardRemove())
            await state.update_data(pending_admin_request=False, user_type='external')
            await show_main_menu(message, state, user_id, lang)
            return
    
    # Oddiy xavfsizlik tekshiruvi
    # Telefon raqam orqali xodimni tekshirish
    is_authorized = await db.verify_employee_by_phone(phone_number, user_id)
    
    if is_authorized:
        await state.update_data(user_type='employee')
        await message.answer(texts[lang]['welcome_menu'], reply_markup=ReplyKeyboardRemove())
        await show_main_menu(message, state, user_id, lang)
    else:
        await message.answer(texts[lang]['verification_fail'], reply_markup=ReplyKeyboardRemove())
        # Qayta urinish imkoniyati
        user_type_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=texts[lang]['employee_button'], callback_data="user_type_employee")],
            [InlineKeyboardButton(text=texts[lang]['external_button'], callback_data="user_type_external")]
        ])
        await message.answer(texts[lang]['ask_user_type'], reply_markup=user_type_keyboard)
        await state.set_state(MainForm.user_type_selection)


@dp.message(MainForm.external_contact, F.contact)
async def process_external_contact(message: Message, state: FSMContext):
    """Tashqi shaxslar uchun kontakt qabul qilish"""
    lang = await get_user_lang(state)
    user_id = message.from_user.id
    phone_number = message.contact.phone_number
    
    # Telefon raqamni bazaga saqlash
    try:
        await db.update_user_phone_number(user_id, phone_number)
    except Exception:
        pass
    
    await state.update_data(user_type='external')
    await message.answer(texts[lang]['welcome_menu'], reply_markup=ReplyKeyboardRemove())
    await show_main_menu(message, state, user_id, lang)


async def show_main_menu(message: Message, state: FSMContext, user_id: int, lang: str):
    """Foydalanuvchi turiga qarab asosiy menyuni ko'rsatish"""
    user_data = await state.get_data()
    user_type = user_data.get('user_type', 'external')
    
    if await db.is_admin(user_id):
        keyboard = get_admin_main_keyboard(lang)
    elif user_type == 'employee':
        keyboard = get_employee_keyboard(lang)
    else:
        keyboard = get_external_user_keyboard(lang)
    
    await message.answer(texts[lang]['welcome_menu'], reply_markup=keyboard)
    await state.set_state(MainForm.main_menu)


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
        
        if await db.is_admin(user_id):
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
    dp.include_router(product_router)
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

