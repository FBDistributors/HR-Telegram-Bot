# savol_javob.py fayli (FAQ bo'limi)

import logging
import os
import google.generativeai as genai
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

# --- BU FAYL UCHUN ALOHIDA ROUTER YARATAMIZ ---
router = Router()

# --- Sozlamalar va Konfiguratsiya ---

# Gemini API kalitini .env faylidan olish
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logging.critical("Gemini API kaliti topilmadi! .env faylini tekshiring.")
else:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

# Ruxsat etilgan telefon raqamlari va operator manzilini .env faylidan olish
AUTHORIZED_NUMBERS = os.getenv("AUTHORIZED_NUMBERS", "")
OPERATOR_USERNAME = os.getenv("OPERATOR_USERNAME", "admin") # Agar topilmasa, standart "admin"

# Bilimlar bazasini fayldan o'qish uchun funksiya
def load_knowledge_base(filename: str) -> str:
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"Bilimlar bazasi fayli topilmadi: {filename}")
        return "Kompaniya haqida ma'lumot topilmadi."

knowledge_base_uz = load_knowledge_base('knowledge_base_uz.txt')
knowledge_base_ru = load_knowledge_base('knowledge_base_ru.txt')

# --- FAQ Uchun Matnlar ---
texts = {
    'uz': {
        'faq_welcome': "Kompaniyamiz haqida savolingiz bo'lsa, marhamat, yozing. Bosh menyuga qaytish uchun 'Bosh menyu' tugmasidan foydalaning.",
        'faq_no_answer': f"Kechirasiz, bu savolingizga javob topa olmadim. Iltimos, savolingizni boshqacha tarzda bering yoki @{OPERATOR_USERNAME} orqali operator bilan bog'laning.",
        'knowledge_base': knowledge_base_uz,
        'faq_auth_fail': "Kechirasiz, sizda bu bo'limdan foydalanish uchun ruxsat yo'q.",
        'faq_auth_invalid': "Iltimos, shaxsingizni tasdiqlash uchun 'Kontaktimni ulashish' tugmasidan foydalaning.",
        'faq_limit_reached': "Siz savollar limitiga yetdingiz. Suhbatni qaytadan boshlash uchun 'Bosh menyu' tugmasidan foydalaning.",
        'gemini_error': "Kechirasiz, hozirda javob berishda texnik muammo yuzaga keldi. Iltimos, birozdan so'ng qayta urinib ko'ring.",
        'main_menu_button': "🏠 Bosh menyu",
    },
    'ru': {
        'faq_welcome': "Если у вас есть вопросы о нашей компании, пожалуйста, напишите. Используйте кнопку 'Главное меню' для возврата.",
        'faq_no_answer': f"Извините, я не смог найти ответ на ваш вопрос. Пожалуйста, перефразируйте его или свяжитесь с оператором через @{OPERATOR_USERNAME}.",
        'knowledge_base': knowledge_base_ru,
        'faq_auth_fail': "К сожалению, у вас нет доступа к этому разделу.",
        'faq_auth_invalid': "Пожалуйста, используйте кнопку 'Поделиться моим контактом' для подтверждения вашей личности.",
        'faq_limit_reached': "Вы достигли лимита вопросов. Чтобы начать заново, воспользуйтесь кнопкой 'Главное меню'.",
        'gemini_error': "Извините, в данный момент возникла техническая проблема с ответом. Пожалуйста, попробуйте позже.",
        'main_menu_button': "🏠 Главное меню",
    }
}

# --- FAQ Uchun FSM Holatlari ---
class FaqForm(StatesGroup):
    verification = State() # Kontakt orqali tekshirish holati
    in_process = State()   # Savol-javob jarayoni holati

# Foydalanuvchi tanlagan tilni olish uchun yordamchi funksiya
async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')

# --- FAQ Bo'limi Handler'lari ---
# E'tibor bering, endi @dp.message o'rniga @router.message ishlatiladi

@router.message(FaqForm.verification, F.contact)
async def process_faq_verification(message: Message, state: FSMContext):
    lang = await get_user_lang(state)
    user_phone_number = message.contact.phone_number
    # Raqamni xalqaro formatga keltirish (+ belgisini qo'shish)
    if not user_phone_number.startswith('+'):
        user_phone_number = '+' + user_phone_number

    # .env faylidagi ruxsat etilgan raqamlar ro'yxati
    authorized_numbers_list = [num.strip() for num in AUTHORIZED_NUMBERS.split(',')]

    # Doimiy "Bosh menyu" tugmasi
    persistent_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts[lang]['main_menu_button'])]],
        resize_keyboard=True
    )

    if user_phone_number in authorized_numbers_list:
        logging.info(f"Foydalanuvchi {user_phone_number} FAQ bo'limiga kirdi.")
        await message.answer(texts[lang]['faq_welcome'], reply_markup=persistent_keyboard)
        # Savollar soni va suhbat tarixini nollashtirish
        await state.update_data(faq_question_count=0, chat_history=[])
        await state.set_state(FaqForm.in_process)
    else:
        logging.warning(f"Ruxsatsiz urinish: {user_phone_number}")
        await message.answer(texts[lang]['faq_auth_fail'], reply_markup=persistent_keyboard)
        await state.clear() # Agar ruxsat bo'lmasa, holatni tozalash

@router.message(FaqForm.verification)
async def process_faq_verification_invalid(message: Message, state: FSMContext):
    # Agar foydalanuvchi kontakt o'rniga matn yoki boshqa narsa yuborsa
    lang = await get_user_lang(state)
    await message.reply(texts[lang]['faq_auth_invalid'])

@router.message(FaqForm.in_process, F.text)
async def handle_faq_questions(message: Message, state: FSMContext):
    # Agar Gemini API kaliti sozlanmagan bo'lsa, ishni to'xtatish
    if not GEMINI_API_KEY:
        await message.reply("Kechirasiz, savol-javob moduli sozlanmagan.")
        return

    lang = await get_user_lang(state)
    data = await state.get_data()

    # Savollar limitini tekshirish
    question_count = data.get('faq_question_count', 0)
    if question_count >= 10:
        await message.reply(texts[lang]['faq_limit_reached'])
        await state.clear()
        return

    user_question = message.text
    knowledge_base = texts[lang]['knowledge_base']
    chat_history = data.get('chat_history', [])

    # Suhbat tarixini Gemini uchun formatlash
    formatted_history = ""
    for entry in chat_history:
        formatted_history += f"Foydalanuvchi: {entry['user']}\nYordamchi: {entry['assistant']}\n---\n"
    
    # Gemini uchun so'rov (prompt) yaratish
    prompt = f"""
Ssenariy: Sen O'zbekistondagi kompaniyaning HR yordamchisisan.
Vazifang: Foydalanuvchining savoliga faqat va faqat quyida berilgan "BILIMLAR BAZASI"dagi ma'lumotlarga asoslanib javob berish.
Til: Javobni foydalanuvchi tanlagan tilda ({lang}) ber.
Qo'shimcha qoidalar:
1. Agar foydalanuvchi "rahmat", "tashakkur" kabi minnatdorchilik bildirsa yoki xayrlashsa, bilimlar bazasidan foydalanma. "Arzimaydi, yana savollaringiz bo'lsa, bemalol murojaat qiling!" kabi xushmuomala javob qaytar.
2. Agar savolga javob "BILIMLAR BAZASI"da mavjud bo'lmasa, o'zingdan javob to'qima. Aniq qilib "{texts[lang]['faq_no_answer']}" deb javob ber.
3. Javobni qisqa, aniq va lirik chekinishlarsiz ber.

--- BILIMLAR BAZASI ---
{knowledge_base}
--- BILIMLAR BAZASI TUGADI ---

--- SUHBAT TARIXI ---
{formatted_history}
--- SUHBAT TARIXI TUGADI ---

FOYDALANUVCHINING SAVOLI: "{user_question}"
"""
    
    bot_response_text = ""
    try:
        # Gemini modeliga asinxron so'rov yuborish
        response = await model.generate_content_async(prompt)
        bot_response_text = response.text
        await message.reply(bot_response_text)
    except Exception as e:
        logging.error(f"FAQ Gemini xatoligi: {e}")
        bot_response_text = texts[lang]['gemini_error']
        await message.reply(bot_response_text)

    # Suhbat tarixini yangilash
    chat_history.append({'user': user_question, 'assistant': bot_response_text})
    
    # Eskirgan xabarlarni olib tashlash uchun tarixni cheklash
    MAX_HISTORY_LENGTH = 10 
    if len(chat_history) > MAX_HISTORY_LENGTH:
        chat_history = chat_history[-MAX_HISTORY_LENGTH:]

    # Holatdagi ma'lumotlarni yangilash
    await state.update_data(chat_history=chat_history, faq_question_count=question_count + 1)
