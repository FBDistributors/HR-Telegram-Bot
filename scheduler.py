# scheduler.py fayli

import asyncio
import logging
import os
import google.generativeai as genai
from aiogram import Bot

# Boshqa modullarni import qilish
import database as db
from keyboards import texts
from savol_javob import load_knowledge_base # savol_javob.py dan funksiyani import qilamiz

# Sozlamalar
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

async def check_unanswered_questions(bot: Bot):
    """
    Har soatda bir marta ishga tushib, javobsiz savollarni tekshiradi
    va javob topilsa, foydalanuvchiga yuboradi.
    """
    while True:
        await asyncio.sleep(3600) # 1 soat kutish (3600 sekund)
        logging.info("Javobsiz savollarni avtomatik tekshirish boshlandi...")

        if not GEMINI_API_KEY:
            logging.warning("Scheduler: Gemini API kaliti topilmadi, tekshiruv o'tkazib yuborildi.")
            continue

        pending_questions = db.get_pending_questions()
        if not pending_questions:
            logging.info("Scheduler: Javob kutilayotgan savollar topilmadi.")
            continue

        for q_id, user_id, user_full_name, question, lang in pending_questions:
            try:
                knowledge_base = load_knowledge_base(lang)
                no_answer_text_for_ai = texts[lang]['faq_no_answer_ai']

                # AI ga savolni qayta yuborish
                prompt = f"""
Ssenariy: Sen HR yordamchisan. Quyida foydalanuvchining savoli va bilimlar bazasi keltirilgan.
Vazifang: Savolga FAQAT bilimlar bazasidagi ma'lumotlarga asoslanib javob berish.
Til: Javobni {lang} tilida ber.
Qoida: Agar javob topa olmasang, FAQATGINA "{no_answer_text_for_ai}" deb javob ber.

--- BILIMLAR BAZASI ---
{knowledge_base}
--- BILIMLAR BAZASI TUGADI ---
FOYDALANUVCHINING SAVOLI: "{question}"
"""
                response = await model.generate_content_async(prompt)
                bot_response_text = response.text.strip()

                # Agar AI endi javob topsa
                if no_answer_text_for_ai not in bot_response_text:
                    logging.info(f"Savol ID {q_id} uchun javob topildi. Foydalanuvchi {user_id} ga yuborilmoqda.")
                    
                    # Foydalanuvchiga xabar yuborish
                    notification_text = texts[lang]['faq_answer_found_notification'].format(
                        full_name=user_full_name,
                        question=question,
                        answer=bot_response_text
                    )
                    await bot.send_message(user_id, notification_text, parse_mode="Markdown")
                    
                    # Savolni "javob berildi" deb belgilash
                    db.mark_question_as_answered(q_id)
                    
                    # Telegramga spam bo'lmasligi uchun kichik pauza
                    await asyncio.sleep(1)

            except Exception as e:
                logging.error(f"Scheduler: Savol ID {q_id} ni tekshirishda xatolik: {e}")

