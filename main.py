import asyncio
import logging
import io
import docx
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import os
from dotenv import load_dotenv

load_dotenv()

# --- SOZLAMALAR ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HR_GROUP_ID = os.getenv("HR_GROUP_ID")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- TILLAR UCHUN LUG'AT (YANGILANGAN) ---
texts = {
    'uz': {
        'welcome': "Assalomu alaykum! Tilni tanlang.",
        'ask_name': "To'liq ism-familiyangizni kiriting:",
        'ask_experience': "Rahmat! Endi tajribangiz haqida yozing (masalan, '2 yil SMM sohasida').",
        'ask_portfolio': "Ajoyib! Endi rezyumeingizni PDF yoki DOCX formatida yuboring.",
        'analyzing': "Ma'lumotlar qabul qilindi. Hozir sun'iy intellekt yordamida tahlil qilinmoqda, bir oz kuting...",
        'goodbye_user': "Arizangiz uchun rahmat! Ma'lumotlaringiz muvaffaqiyatli qabul qilindi. Agar nomzodingiz ma'qul topilsa, biz siz bilan tez orada bog'lanamiz. ✅",
        'file_error': "Iltimos, rezyumeni faqat PDF yoki DOCX formatida yuboring.",
        'hr_notification': """🔔 Yangi nomzod!

👤 **Ism:** {name}
📝 **Qisqa tajriba:** {experience}
-------------------
🤖 **Sun'iy Intellekt Xulosasi:**
{summary}""",
        'gemini_file_prompt': """...""", # o'zgarishsiz, qisqartirildi
        'gemini_text_prompt': """..."""  # o'zgarishsiz, qisqartirildi
    },
    'ru': {
        'welcome': "Здравствуйте! Выберите язык.",
        'ask_name': "Введите ваше полное имя и фамилию:",
        'ask_experience': "Спасибо! Теперь опишите ваш опыт (например, '2 года в сфере SMM').",
        'ask_portfolio': "Отлично! Теперь отправьте ваше резюме в формате PDF или DOCX.",
        'analyzing': "Данные получены. Сейчас они анализируются с помощью искусственного интеллекта, подождите немного...",
        'goodbye_user': "Спасибо за вашу заявку! Ваши данные успешно приняты. Мы свяжемся с вами в ближайшее время, если ваша кандидатура будет одобрена. ✅",
        'file_error': "Пожалуйста, отправьте резюме только в формате PDF или DOCX.",
        'hr_notification': """🔔 Новый кандидат!

👤 **Имя:** {name}
📝 **Краткий опыт:** {experience}
-------------------
🤖 **Заключение Искусственного Интеллекта:**
{summary}""",
        'gemini_file_prompt': """...""", # o'zgarishsiz, qisqartirildi
        'gemini_text_prompt': """..."""  # o'zgarishsiz, qisqartirildi
    }
}


# --- BOTNING XOTIRASI (FSM) ---
class Form(StatesGroup):
    language_selection = State()
    name = State()
    experience = State()
    resume_file = State()

# --- ASOSIY BOT QISMI ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
# ... qolgan qismlar o'zgarishsiz ...
language_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")], [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")]])

async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')

@dp.message(Command("start"))
async def send_welcome(message: types.Message, state: FSMContext):
    await message.reply(f"{texts['uz']['welcome']}\n{texts['ru']['welcome']}", reply_markup=language_keyboard)
    await state.set_state(Form.language_selection)
@dp.callback_query(Form.language_selection, F.data.startswith('lang_'))
async def process_language_selection(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split('_')[1]
    await state.update_data(language=lang)
    await callback.message.edit_reply_markup()
    await callback.message.answer(texts[lang]['ask_name'])
    await state.set_state(Form.name)
    await callback.answer()
@dp.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(name=message.text)
    await message.answer(texts[lang]['ask_experience'])
    await state.set_state(Form.experience)
@dp.message(Form.experience)
async def process_experience(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(experience=message.text)
    await message.answer(texts[lang]['ask_portfolio'])
    await state.set_state(Form.resume_file)


# PDF YOKI DOCX FAYLLARNI QABUL QILADIGAN HANDLER (YANGILANGAN)
@dp.message(Form.resume_file, F.document)
async def process_resume_file(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    file_mime_type = message.document.mime_type
    
    if file_mime_type not in ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        await message.reply(texts[lang]['file_error'])
        return

    await message.answer(texts[lang]['analyzing'])
    
    file_id = message.document.file_id
    file_info = await bot.get_file(file_id)
    file_bytes_io = await bot.download_file(file_info.file_path)
    
    user_data = await state.get_data()
    gemini_summary = ""

    try:
        # Gemini tahlili (o'zgarishsiz)
        if file_mime_type == "application/pdf":
            pdf_part = {"mime_type": "application/pdf", "data": file_bytes_io.read()}
            prompt = texts[lang]['gemini_file_prompt']
            response = await model.generate_content_async([prompt, pdf_part])
            gemini_summary = response.text
        elif file_mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            document = docx.Document(file_bytes_io)
            resume_text_parts = []
            for para in document.paragraphs: resume_text_parts.append(para.text)
            for table in document.tables:
                for row in table.rows:
                    for cell in row.cells: resume_text_parts.append(cell.text)
            resume_text = "\n".join(resume_text_parts)
            
            if not resume_text.strip():
                 gemini_summary = "DOCX faylidan matn topilmadi."
            else:
                prompt = texts[lang]['gemini_text_prompt'].format(resume_text=resume_text)
                response = await model.generate_content_async(prompt)
                gemini_summary = response.text
    except Exception as e:
        logging.error(f"Faylni tahlil qilishdagi xato: {e}")
        gemini_summary = "Faylni tahlil qilishda xatolik yuz berdi."

    # XULOSANI HR GURUHIGA YUBORISH (YANGILANGAN MANTIQ)
    hr_notification_template = texts[lang]['hr_notification']
    hr_summary_text = hr_notification_template.format(
        name=user_data.get('name'),
        experience=user_data.get('experience'),
        summary=gemini_summary
    )

    if HR_GROUP_ID:
        await bot.send_message(HR_GROUP_ID, hr_summary_text)
        await bot.send_document(HR_GROUP_ID, file_id) 
    else:
        logging.warning("HR_GROUP_ID belgilanmagan. Xulosa guruhga yuborilmadi.")

    # NOMZODGA STANDART JAVOB YUBORISH
    await message.answer(texts[lang]['goodbye_user'])
    await state.clear()


@dp.message(Form.resume_file)
async def process_resume_invalid(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await message.reply(texts[lang]['file_error'])

async def main():
    if not BOT_TOKEN or not GEMINI_API_KEY:
        logging.critical("Bot tokeni yoki Gemini API kaliti topilmadi!")
        return
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())