# savol_javob.py fayli (Tozalangan va to'g'ri ishlaydigan versiya)

import logging
import os
import google.generativeai as genai
from aiogram import Bot
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
import textwrap
import importlib.metadata

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
    model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')

async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')


def _safe_log(message: str):
    """Log helper that won't crash on non-encodable characters in some consoles."""
    try:
        logging.debug(message)
    except Exception:
        try:
            logging.debug(message.encode('ascii', 'ignore').decode())
        except Exception:
            logging.debug(repr(message))

# --- FAQ Bo'limi Handler'lari ---

@router.message(FaqForm.verification, F.contact)
async def process_faq_verification(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    user_phone_number = message.contact.phone_number

    # --- YANGI QO'SHILGAN BLOK ---
    # Har ehtimolga qarshi, foydalanuvchi mavjudligini tekshiramiz.
    # Agar u bazada bo'lmasa, shu yerda qo'shib qo'yamiz.
    # db.add_user funksiyasi agar foydalanuvchi mavjud bo'lsa, xato bermaydi, shunchaki o'tib ketadi.
    await db.add_user(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username
    )
    # --- YANGI BLOK TUGADI ---

    # Endi raqamni saqlaymiz (foydalanuvchi bazada borligi kafolatlangan)
    await db.update_user_phone_number(message.from_user.id, user_phone_number)

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
    # --- DIAGNOSTIKA KODI BOSHLANDI ---
    try:
        ggai_version = importlib.metadata.version('google-generativeai')
        _safe_log(f"[DIAGNOSTIC] google-generativeai: {ggai_version}")
    except importlib.metadata.PackageNotFoundError:
        _safe_log("[DIAGNOSTIC] google-generativeai not installed")
    # --- DIAGNOSTIKA KODI TUGADI ---

    if not GEMINI_API_KEY:
        await message.reply("Kechirasiz, savol-javob moduli sozlanmagan.")
        return

    lang = await get_user_lang(state)
    user_question = message.text
    user_id = message.from_user.id
    
    # --- DIAGNOSTIKA QISMI BOSHLANDI ---
    _safe_log("--- SAVOLGA JAVOB BERISH JARAYONI ---")
    
    # 1. Suhbat tarixini bazadan olamiz
    db_history = await db.get_chat_history(user_id)
    formatted_history = "\n".join(
        [f"{'Foydalanuvchi' if msg.role == 'user' else 'Yordamchi'}: {msg.message}" for msg in db_history]
    )
    _safe_log("1. Olingan suhbat tarixi: [omitted in logs]")

    # 2. Bilimlar bazasini bazadan olamiz
    knowledge_base = await db.get_knowledge_base_as_string(lang)
    _safe_log("2. Bilimlar bazasi yuklandi: [omitted in logs]")

    no_answer_text_for_ai = texts[lang]['faq_no_answer_ai']
    
    # 3. Promptni suhbat tarixi va YANGI FORMATLASH QOIDALARI bilan yangilaymiz
    prompt = f"""
    Ssenariy: Sen O'zbekistondagi kompaniyaning HR yordamchisisan.
    Vazifang: Foydalanuvchining savoliga javob berishda avvalgi suhbat tarixini ("SUHBAT TARIXI") va bilimlar bazasini ("BILIMLAR BAZASI") inobatga ol.
    Til: Javobni foydalanuvchi tanlagan tilda ({lang}) ber.

    **JAVOB FORMATI UCHUN QAT'IY QOIDA:**
    Javobni o'qish uchun maksimal darajada qulay, tartibli va chiroyli qil. Yaxlit, uzun matndan MUTLAQO qoch. **HTML teglaridan foydalan.**
    - **Sarlavhalardan foydalan:** Ma'lumotni mantiqiy qismlarga ajrat va har bir qismni <b>qalin</b> shriftda yozilgan sarlavha bilan boshla.
    - **Emoji qo'sh:** Har bir sarlavha yoki muhim punkt oldidan unga mos keladigan emoji (masalan, 🏢 Kompaniya, 📅 Sana, 👥 Asoschilar, 📍 Manzil, 🎁 Imtiyozlar) qo'y.
    - **Ro'yxatlardan foydalan:** Agar javob bir nechta punktlardan iborat bo'lsa (masalan, ta'sischilar, imtiyozlar ro'yxati), ularni albatta ro'yxat (list) ko'rinishida formatla. Har bir punktni yangi qatordan chiroyli belgi bilan boshla. Masalan, `-` yoki `*` o'rniga `🔹`, `✅`, `▫️` yoki `▪️` kabi belgilardan foydalan.
    - **Misol:** "Kompaniya haqida ma'lumot" so'ralganda, javob quyidagicha ko'rinishda bo'lishi kerak:

    🏢 <b>Umumiy ma'lumot</b>
    FB Distributors Group - "Abadiy Go'zallik" degan ma'noni anglatadi...

    📅 <b>Tashkil topgan sana</b>
    2023-yil 17-may

    👥 <b>Ta'sischilar</b>
    🔹 Xaknazarov Bobir Xusnitdinovich
    🔹 Xaknazarov Faxriddin Xusnitdinovich

    📍 <b>Manzil</b>
    Toshkent shahri, Mirobod tumani...

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
    _safe_log("3. AI prompt tayyor: [omitted in logs]")

    bot_response_text = ""
    try:
        await bot.send_chat_action(chat_id=user_id, action="typing")
        
        response = await model.generate_content_async(prompt)
        bot_response_text = response.text.strip()
    except Exception as e:
        logging.error(f"FAQ Gemini xatoligi: {e}")
        # AI xatoligida ham foydalanuvchiga texnik xabar bermaymiz; 
        # avtomatik ravishda "javob topilmadi" oqimiga yo'naltiramiz
        bot_response_text = no_answer_text_for_ai

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
        # 1. AI'dan kelgan xom javobni olamiz va ```html``` kabi belgilardan tozalaymiz
        processed_text = bot_response_text.strip()
        if processed_text.startswith('```'):
            lines = processed_text.split('\n')
            processed_text = '\n'.join(lines[1:-1])
        processed_text = processed_text.strip()

        # 2. Telegram qo'llab-quvvatlamaydigan HTML teglarni oddiy qatorga aylantiramiz
        import re
        processed_text = processed_text.replace("<p>", "").replace("</p>", "\n")
        processed_text = processed_text.replace("<ul>", "").replace("</ul>", "\n")
        processed_text = processed_text.replace("<li>", "").replace("</li>", "\n")
        processed_text = processed_text.replace("<br>", "\n")
        
        # Ketma-ket kelgan bo'sh qatorlarni bittaga qisqartiramiz
        final_html = re.sub(r'\n{2,}', '\n', processed_text).strip()

        try:
            # 3. Tayyor, tozalangan HTMLni yuboramiz
            await message.reply(final_html, parse_mode="HTML")
        except Exception as e:
            logging.error(f"HTML parse xatoligi: {e}. Javob oddiy matnda yuborilmoqda.")
            # Xato bo'lsa, barcha teglarni olib tashlab yuboramiz
            clean_text = re.sub('<[^<]+?>', '', final_html)
            await message.reply(clean_text)

    # 4. Yangi savol-javobni bazaga saqlaymiz
    await db.add_chat_message(user_id, 'user', user_question)
    
    # Gemini "javob topolmadim" desa ham, shuni tarixga yozamiz
    if no_answer_text_for_ai in bot_response_text:
        await db.add_chat_message(user_id, 'assistant', texts[lang]['faq_no_answer_user'])
    else:
        # Endi bazaga xom javobni emas, balki biz formatlagan toza javobni saqlaymiz
        await db.add_chat_message(user_id, 'assistant', final_html)

