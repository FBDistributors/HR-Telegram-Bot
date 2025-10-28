# scheduler.py fayli (PostgreSQL bilan to'g'ri ishlaydigan versiya)

import asyncio
import logging
import os
import google.generativeai as genai
from aiogram import Bot

# Boshqa modullarni import qilish
import database as db
from keyboards import texts

# Sozlamalar
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')

async def cleanup_expired_documents():
    """
    Har kun bir marta ishga tushib, muddati o'tgan hujjatlarni tozalaydi.
    """
    while True:
        await asyncio.sleep(86400) # 24 soat kutish (86400 sekund)
        logging.info("Muddati o'tgan hujjatlarni tozalash boshlandi...")
        
        try:
            await db.delete_expired_documents()
            logging.info("Muddati o'tgan hujjatlarni tozalash muvaffaqiyatli yakunlandi.")
        except Exception as e:
            logging.error(f"Muddati o'tgan hujjatlarni tozalashda xatolik: {e}")


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

        # <<< O'ZGARTIRILDI: Bazadan obyektlar ro'yxatini olamiz >>>
        pending_questions = await db.get_pending_questions()
        if not pending_questions:
            logging.info("Scheduler: Javob kutilayotgan savollar topilmadi.")
            continue
        
        # <<< O'ZGARTIRILDI: Endi obyektlar bo'yicha sikl ishlatamiz >>>
        for q in pending_questions:
            try:
                # Obyekt ichidan ma'lumotlarni olamiz
                lang = q.lang or 'uz' # Agar til belgilanmagan bo'lsa, standart 'uz' tilini olamiz
                knowledge_base = await db.get_knowledge_base_as_string(lang)
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
FOYDALANUVCHINING SAVOLI: "{q.question}"
"""
                response = await model.generate_content_async(prompt)
                bot_response_text = response.text.strip()

                # Agar AI endi javob topsa
                if no_answer_text_for_ai not in bot_response_text:
                    logging.info(f"Savol ID {q.id} uchun javob topildi. Foydalanuvchi {q.user_id} ga yuborilmoqda.")
                    
                    # Foydalanuvchiga xabar yuborish
                    notification_text = texts[lang]['faq_answer_found_notification'].format(
                        full_name=q.full_name,
                        question=q.question,
                        answer=bot_response_text
                    )
                    await bot.send_message(q.user_id, notification_text, parse_mode="Markdown")
                    
                    # <<< O'ZGARTIRILDI: Savolni "javob berildi" deb belgilaymiz >>>
                    await db.mark_question_as_answered(q.id)
                    
                    # Telegramga spam bo'lmasligi uchun kichik pauza
                    await asyncio.sleep(1)

            except Exception as e:
                logging.error(f"Scheduler: Savol ID {q.id} ni tekshirishda xatolik: {e}")
