# savol_javob.py fayli (Tozalangan va to'g'ri ishlaydigan versiya)

import logging
import os
import google.generativeai as genai
from aiogram import Bot
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

import database as db
from states import MainForm, FaqForm
from keyboards import texts, get_user_keyboard, get_admin_main_keyboard

router = Router()

# Sozlamalar
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")
HR_GROUP_ID = os.getenv("HR_GROUP_ID")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')

# --- FAQ Bo'limi Handler'lari ---

@router.message(FaqForm.verification, F.contact)
async def process_faq_verification(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    user_phone_number = message.contact.phone_number

    is_authorized = await db.verify_employee_by_phone(user_phone_number, message.from_user.id)
    
    await state.update_data(language=lang)

    if str(message.from_user.id) == ADMIN_ID:
        keyboard = get_admin_main_keyboard(lang)
    else:
        keyboard = get_user_keyboard(lang)

    if is_authorized:
        logging.info(f"Xodim {user_phone_number} FAQ bo'limiga kirdi.")
        await message.answer(texts[lang]['faq_welcome'], reply_markup=keyboard)
        await state.set_state(FaqForm.in_process)
    else:
        logging.warning(f"Ruxsatsiz urinish (xodim emas): {user_phone_number}")
        await message.answer(texts[lang]['faq_auth_fail'], reply_markup=keyboard)
        await state.set_state(MainForm.main_menu)

@router.message(FaqForm.verification)
async def process_faq_verification_invalid(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await message.reply(texts[lang]['faq_auth_prompt'])


@router.message(FaqForm.in_process, F.text)
async def handle_faq_questions(message: types.Message, state: FSMContext, bot: Bot):
    if not GEMINI_API_KEY:
        await message.reply("Kechirasiz, savol-javob moduli sozlanmagan.")
        return

    lang = await get_user_lang(state)
    user_question = message.text
    user_id = message.from_user.id
    
    # --- DIAGNOSTIKA QISMI BOSHLANDI ---
    print("\n--- SAVOLGA JAVOB BERISH JARAYONI ---")
    
    # 1. Suhbat tarixini bazadan olamiz
    db_history = await db.get_chat_history(user_id)
    formatted_history = "\n".join(
        [f"{'Foydalanuvchi' if msg.role == 'user' else 'Yordamchi'}: {msg.message}" for msg in db_history]
    )
    print(f"1. Olingan suhbat tarixi:\n---\n{formatted_history}\n---")

    # 2. Bilimlar bazasini bazadan olamiz
    knowledge_base = await db.get_knowledge_base_as_string(lang)
    print(f"2. Bazadan olingan bilimlar bazasi:\n---\n{knowledge_base}\n---")

    no_answer_text_for_ai = texts[lang]['faq_no_answer_ai']
    
    # 3. Promptni suhbat tarixi bilan birga yangilaymiz
    prompt = f"""
Ssenariy: Sen O'zbekistondagi kompaniyaning HR yordamchisisan.
Vazifang: Foydalanuvchining savoliga javob berishda avvalgi suhbat tarixini ("SUHBAT TARIXI") va bilimlar bazasini ("BILIMLAR BAZASI") inobatga ol.
Til: Javobni foydalanuvchi tanlagan tilda ({lang}) ber.
Qo'shimcha qoidalar:
1. Agar savol avvalgi suhbatning mantiqiy davomi bo'lsa, shuni hisobga olib javob ber.
2. {texts[lang]['ai_rule_thanks']}
3. Agar savolga javob "BILIMLAR BAZASI"da mavjud bo'lmasa, o'zingdan javob to'qima. Aniq qilib "{no_answer_text_for_ai}" deb javob ber. Hech qanday qo'shimcha matn qo'shma.
4. Javobni "BILIMLAR BAZASIGA ko'ra" degan so'zlar bilan boshlama. To'g'ridan-to'g'ri javobni o'zini ber. 

--- SUHBAT TARIXI ---
{formatted_history}
--- SUHBAT TARIXI TUGADI ---

--- BILIMLAR BAZASI ---
{knowledge_base}
--- BILIMLAR BAZASI TUGADI ---

ENG SO'NGGI SAVOL: "{user_question}"
"""
    print(f"3. Sun'iy intellektga yuborilayotgan to'liq prompt:\n---\n{prompt}\n---")
    # --- DIAGNOSTIKA QISMI TUGADI ---

    bot_response_text = ""
    try:
        await bot.send_chat_action(chat_id=user_id, action="typing")
        
        response = await model.generate_content_async(prompt)
        bot_response_text = response.text.strip()
    except Exception as e:
        logging.error(f"FAQ Gemini xatoligi: {e}")
        bot_response_text = "Texnik xatolik yuz berdi, iltimos keyinroq urinib ko'ring."

    # Gemini javobiga qarab ish tutamiz
    if no_answer_text_for_ai in bot_response_text:
        await db.add_unanswered_question(
            user_id=user_id,
            full_name=message.from_user.full_name,
            question=user_question,
            lang=lang
        )
        if HR_GROUP_ID:
            hr_notification = texts[lang]['faq_no_answer_hr_notification'].format(
                full_name=message.from_user.full_name,
                question=user_question
            )
            try:
                await bot.send_message(HR_GROUP_ID, hr_notification, parse_mode="Markdown")
            except Exception as e:
                logging.error(f"HR guruhiga javobsiz savol haqida yuborishda xato: {e}")
        
        await message.reply(texts[lang]['faq_no_answer_user'])
    else:
        await message.reply(bot_response_text)

    # 4. Yangi savol-javobni bazaga saqlaymiz
    await db.add_chat_message(user_id, 'user', user_question)
    
    # Gemini "javob topolmadim" desa ham, shuni tarixga yozamiz
    if no_answer_text_for_ai in bot_response_text:
        await db.add_chat_message(user_id, 'assistant', texts[lang]['faq_no_answer_user'])
    else:
        await db.add_chat_message(user_id, 'assistant', bot_response_text)

