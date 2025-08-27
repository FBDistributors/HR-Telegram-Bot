# savol_javob.py fayli (Menyuni doimiy ko'rsatadigan versiya)

import logging
import os
import google.generativeai as genai
from aiogram import Bot
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

# Yangi states va keyboards fayllaridan import qilish
import database as db
from states import MainForm, FaqForm
from keyboards import texts, get_user_keyboard, get_admin_keyboard

router = Router()

# Sozlamalar
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AUTHORIZED_NUMBERS = os.getenv("AUTHORIZED_NUMBERS", "")
OPERATOR_USERNAME = os.getenv("OPERATOR_USERNAME", "admin")
ADMIN_ID = os.getenv("ADMIN_ID")
HR_GROUP_ID = os.getenv("HR_GROUP_ID")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

# Bilimlar bazasini yuklash funksiyasi
def load_knowledge_base(lang: str) -> str:
    """
    Kerakli tildagi bilimlar bazasini fayldan o'qish uchun funksiya.
    """
    filename = f"knowledge_base_{lang}.txt"
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"Bilimlar bazasi fayli topilmadi: {filename}")
        if lang == 'ru':
            return "База знаний для русского языка не найдена."
        return "O'zbek tili uchun bilimlar bazasi topilmadi."


async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')

# --- FAQ Bo'limi Handler'lari ---

@router.message(FaqForm.verification, F.contact)
async def process_faq_verification(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    user_phone_number = message.contact.phone_number
    if not user_phone_number.startswith('+'):
        user_phone_number = '+' + user_phone_number

    authorized_numbers_list = [num.strip() for num in AUTHORIZED_NUMBERS.split(',')]
    await state.update_data(language=lang)

    # Foydalanuvchining kimligiga qarab to'g'ri menyuni aniqlash
    if str(message.from_user.id) == ADMIN_ID:
        keyboard = get_admin_keyboard(lang)
    else:
        keyboard = get_user_keyboard(lang)

    if user_phone_number in authorized_numbers_list:
        logging.info(f"Foydalanuvchi {user_phone_number} FAQ bo'limiga kirdi.")
        await message.answer(texts[lang]['faq_welcome'], reply_markup=keyboard)
        await state.update_data(faq_question_count=0, chat_history=[])
        await state.set_state(FaqForm.in_process)
    else:
        logging.warning(f"Ruxsatsiz urinish: {user_phone_number}")
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
    data = await state.get_data()
    
    knowledge_base = load_knowledge_base(lang)
    
    user_question = message.text
    chat_history = data.get('chat_history', [])

    # --- MUHIM TUZATISH: "Javob yo'q" matnini to'g'ri tilda keyboards.py dan olish ---
    no_answer_text_for_ai = texts[lang]['faq_no_answer_ai']
    
    prompt = f"""
Ssenariy: Sen O'zbekistondagi kompaniyaning HR yordamchisisan.
Vazifang: Foydalanuvchining savoliga faqat va faqat quyida berilgan "BILIMLAR BAZASI"dagi ma'lumotlarga asoslanib javob berish.
Til: Javobni foydalanuvchi tanlagan tilda ({lang}) ber.
Qo'shimcha qoidalar:
1. Agar foydalanuvchi "rahmat", "tashakkur" kabi minnatdorchilik bildirsa yoki xayrlashsa, bilimlar bazasidan foydalanma. "Arzimaydi, yana savollaringiz bo'lsa, bemalol murojaat qiling!" kabi xushmuomala javob qaytar.
2. Agar savolga javob "BILIMLAR BAZASI"da mavjud bo'lmasa, o'zingdan javob to'qima. Aniq qilib "{no_answer_text_for_ai}" deb javob ber. Hech qanday qo'shimcha matn qo'shma.

--- BILIMLAR BAZASI ---
{knowledge_base}
--- BILIMLAR BAZASI TUGADI ---
FOYDALANUVCHINING SAVOLI: "{user_question}"
"""
    
    bot_response_text = ""
    try:
        response = await model.generate_content_async(prompt)
        bot_response_text = response.text.strip()
    except Exception as e:
        logging.error(f"FAQ Gemini xatoligi: {e}")
        bot_response_text = "Texnik xatolik."

    # --- MUHIM TUZATISH: Javobni to'g'ri tilda tekshirish ---
    if no_answer_text_for_ai in bot_response_text:
        db.add_unanswered_question(
            user_id=message.from_user.id,
            full_name=message.from_user.full_name,
            question=user_question
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

    chat_history.append({'user': user_question, 'assistant': bot_response_text})
    await state.update_data(chat_history=chat_history)