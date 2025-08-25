# admin_panel.py fayli (Ko'p tilli tizim bilan to'liq ishlaydigan yakuniy versiya)

import os
import logging
from aiogram import Bot, Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

import database as db
# keyboards va states fayllaridan kerakli qismlarni import qilamiz
from keyboards import texts, get_admin_keyboard
from states import AdminForm, MainForm

router = Router()

ADMIN_ID = os.getenv("ADMIN_ID")

async def get_user_lang(state: FSMContext):
    """Foydalanuvchi tilini FSM holatidan oladi"""
    user_data = await state.get_data()
    return user_data.get('language', 'uz')

# --- ADMIN UCHUN HANDLER ---

@router.message(AdminForm.waiting_for_announcement, F.text)
async def send_announcement_to_all(message: types.Message, state: FSMContext, bot: Bot):
    if str(message.from_user.id) != ADMIN_ID:
        return

    # Foydalanuvchi tanlagan tilni holatdan olamiz
    lang = await get_user_lang(state)
    
    # Xabarni to'g'ri tilda yuborish
    await message.answer(texts[lang]['broadcast_started'])

    announcement_text = message.text
    all_user_ids = db.get_all_user_ids()

    if not all_user_ids:
        await message.reply("Ma'lumotlar bazasida foydalanuvchilar topilmadi.", reply_markup=get_admin_keyboard(lang))
        # Jarayon tugagani uchun asosiy menyu holatiga qaytaramiz
        await state.set_state(MainForm.main_menu)
        return

    success_count = 0
    fail_count = 0

    for user_id in all_user_ids:
        try:
            await bot.send_message(chat_id=user_id, text=announcement_text)
            success_count += 1
        except TelegramBadRequest as e:
            logging.warning(f"Foydalanuvchi {user_id} ga xabar yuborib bo'lmadi: {e}")
            fail_count += 1
        except Exception as e:
            logging.error(f"Kutilmagan xatolik {user_id}: {e}")
            fail_count += 1

    # Adminga hisobotni va uning menyusini to'g'ri tilda qaytarib yuboramiz
    report_text = texts[lang]['broadcast_report'].format(
        success_count=success_count, 
        fail_count=fail_count
    )
    await message.answer(
        report_text,
        reply_markup=get_admin_keyboard(lang)
    )
    
    # --- MUHIM TUZATISH: state.clear() o'rniga holatni asosiy menyuga o'tkazamiz ---
    await state.set_state(MainForm.main_menu)
