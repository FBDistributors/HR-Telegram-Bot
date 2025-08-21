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

# --- TILLAR UCHUN LUG'AT (YAKUNIY VERSIYA) ---
texts = {
    'uz': {
        'welcome': "Assalomu alaykum! Tilni tanlang.",
        'ask_name': "To'liq ism sharifingizni (FIO) kiriting:",
        'ask_has_resume': "Ajoyib! Arizani davom ettirish uchun, rezyumeingiz bormi?",
        'button_yes_resume': "✅ Ha, rezyume yuborish",
        'button_no_resume': "❌ Yo'q, suhbatdan o'tish",
        'prompt_for_resume': "Marhamat, rezyumeni PDF yoki DOCX formatida yuboring.",
        'start_convo_application': "Hechqisi yo'q! Keling, suhbat orqali bir nechta savollarga javob bering.",
        'ask_vacancy': "Qaysi vakansiyaga murojaat qilyapsiz?",
        'ask_experience': "Ish tajribangiz haqida yozing (oxirgi ish joyingiz, lavozimingiz, necha yil ishlaganingiz).",
        'ask_salary': "Qancha oylik maosh kutyapsiz? (so'mda, raqam yoki matn bilan yozing)",
        'ask_location': "Yashash manzilingizni kiriting (shahar, tuman).",
        'ask_skills': "Vakansiyaga oid asosiy ko'nikmalaringizni yozing (masalan: Excel, 1C, Python, sotuv).",
        'ask_availability': "Yaqin kunlarda ish boshlashga tayyormisiz?",
        'button_yes': "✅ Ha",
        'button_no': "❌ Yo'q",
        'ask_contact': "Siz bilan bog'lanish uchun telefon raqamingizni kiriting.",
        'goodbye_user': "Barcha ma'lumotlaringiz uchun rahmat! Arizangiz muvaffaqiyatli qabul qilindi. Nomzodingiz ma'qul topilsa, biz siz bilan tez orada bog'lanamiz. ✅",
        'analyzing': "Ma'lumotlar qabul qilindi. Hozir sun'iy intellekt yordamida tahlil qilinmoqda, bir oz kuting...",
        'file_error': "Iltimos, rezyumeni faqat PDF yoki DOCX formatida yuboring.",
        'hr_notification_file': """🔔 **Yangi nomzod (Rezyume bilan)!**

👤 **FIO:** {name}
📄 **Rezyume:** Fayl biriktirildi.
-------------------
{summary}""",
        'hr_notification_convo': """🔔 **Yangi nomzod (Suhbat orqali)!**

👤 **FIO:** {name}
👨‍💼 **Vakansiya:** {vacancy}
-------------------
**Nomzod javoblari:**
- **Tajribasi:** {experience}
- **Maosh kutilmasi:** {salary}
- **Manzili:** {location}
- **Ko'nikmalari:** {skills}
- **Ishga tayyorligi:** {availability}
- **Aloqa:** {contact}
-------------------
{summary}""",
        'gemini_file_prompt': """Sen tajribali HR-menejersan. Ilova qilingan fayl nomzodning rezyumesi hisoblanadi. 
        Ushbu rezyumeni o'qib chiqib, nomzod haqida o'zbek tilida, lotin alifbosida qisqacha va aniq xulosa yoz.
        Tahlil quyidagi formatda bo'lsin, sarlavhalar va ro'yxatlar uchun emoji'lardan foydalan:
        🤖 **Umumiy xulosa:** [Nomzodning tajribasi, ko'nikmalari va ma'lumotlari asosida 2-3 gaplik xulosa]
        ✨ **Kuchli tomonlari:**
        ✅ [Rezyumedan topilgan birinchi kuchli jihat]
        ✅ [Rezyumedan topilgan ikkinchi kuchli jihat]
        📊 **Dastlabki baho:** [Mos keladi / O'ylab ko'rish kerak / Tajribasi kam]""",
        'gemini_text_prompt': """Sen tajribali HR-menejersan. Quyida nomzodning rezyumesidan olingan matn keltirilgan. 
        Ushbu matnni tahlil qilib, nomzod haqida o'zbek tilida, lotin alifbosida qisqacha va aniq xulosa yoz.
        Tahlil quyidagi formatda bo'lsin, sarlavhalar va ro'yxatlar uchun emoji'lardan foydalan:
        🤖 **Umumiy xulosa:** [Nomzodning tajribasi, ko'nikmalari va ma'lumotlari asosida 2-3 gaplik xulosa]
        ✨ **Kuchli tomonlari:**
        ✅ [Rezyumedan topilgan birinchi kuchli jihat]
        ✅ [Rezyumedan topilgan ikkinchi kuchli jihat]
        📊 **Dastlabki baho:** [Mos keladi / O'ylab ko'rish kerak / Tajribasi kam]
        
        Rezyume matni:
        {resume_text}
        """,
        'gemini_convo_prompt': """Sen tajribali HR-menejersan. Quyida nomzodning suhbat orqali bergan javoblari keltirilgan. 
        Ushbu ma'lumotlarni tahlil qilib, nomzod haqida o'zbek tilida, lotin alifbosida qisqacha va aniq xulosa yoz.
        Tahlil quyidagi formatda bo'lsin, emoji'lardan foydalan:
        🤖 **Umumiy xulosa:** [Nomzodning javoblari va vakansiyaga mosligi asosida 2-3 gaplik xulosa]
        ✨ **Kuchli tomonlari:**
        ✅ [Suhbatdan topilgan birinchi kuchli jihat]
        ✅ [Suhbatdan topilgan ikkinchi kuchli jihat]
        📊 **Dastlabki baho:** [Mos keladi / O'ylab ko'rish kerak / Tajribasi kam]"""
    },
    'ru': {
        # ... ruscha versiyasini ham xuddi shunday to'ldirishingiz mumkin ...
    }
}

# --- BOTNING XOTIRASI (FSM) YANGILANDI ---
class Form(StatesGroup):
    language_selection = State()
    name = State()
    has_resume_choice = State()  # Rezyume bor-yo'qligini so'rash holati
    resume_upload = State()      # Rezyumeni kutish holati
    # Suhbat yo'li uchun holatlar
    convo_vacancy = State()
    convo_experience = State()
    convo_salary = State()
    convo_location = State()
    convo_skills = State()
    convo_availability = State()
    convo_contact = State()

# --- ASOSIY BOT QISMI ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')

# --- BOT SUHBATLOGIKASI (QAYTA QURILDI) ---
@dp.message(Command("start"))
async def send_welcome(message: types.Message, state: FSMContext):
    await state.clear()
    language_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")], [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")]])
    await message.reply(f"{texts['uz']['welcome']}\n{texts['ru']['welcome']}", reply_markup=language_keyboard)
    await state.set_state(Form.language_selection)

@dp.callback_query(Form.language_selection, F.data.startswith('lang_'))
async def process_language_selection(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split('_')[1]
    await state.update_data(language=lang)
    await callback.message.delete_reply_markup()
    await callback.message.answer(texts[lang]['ask_name'])
    await state.set_state(Form.name)
    await callback.answer()

@dp.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(name=message.text)
    
    resume_choice_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts[lang]['button_yes_resume'], callback_data="has_resume_yes")],
        [InlineKeyboardButton(text=texts[lang]['button_no_resume'], callback_data="has_resume_no")]
    ])
    await message.answer(texts[lang]['ask_has_resume'], reply_markup=resume_choice_keyboard)
    await state.set_state(Form.has_resume_choice)

@dp.callback_query(Form.has_resume_choice, F.data.startswith('has_resume_'))
async def process_has_resume_choice(callback: types.CallbackQuery, state: FSMContext):
    lang = await get_user_lang(state)
    choice = callback.data.split('_')[2]
    await callback.message.delete_reply_markup()
    
    if choice == "yes":
        await callback.message.answer(texts[lang]['prompt_for_resume'])
        await state.set_state(Form.resume_upload)
    elif choice == "no":
        await callback.message.answer(texts[lang]['start_convo_application'])
        await callback.message.answer(texts[lang]['ask_vacancy'])
        await state.set_state(Form.convo_vacancy)
    await callback.answer()

# === 1-YO'L: Rezyume yuklash uchun handler ===
@dp.message(Form.resume_upload, F.document)
async def process_resume_file(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    # ... (bu qismni avvalgi ishlayotgan kodingizdan to'liq ko'chirib oling) ...
    # ... (PDF/DOCX tahlili, Gemini'ga yuborish, xulosani guruhga yuborish)
    await message.answer(texts[lang]['goodbye_user'])
    await state.clear()


# === 2-YO'L: Suhbat orqali ma'lumot olish ===
@dp.message(Form.convo_vacancy)
async def process_convo_vacancy(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(vacancy=message.text)
    await message.answer(texts[lang]['ask_experience'])
    await state.set_state(Form.convo_experience)

@dp.message(Form.convo_experience)
async def process_convo_experience(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(experience=message.text)
    await message.answer(texts[lang]['ask_salary'])
    await state.set_state(Form.convo_salary)

@dp.message(Form.convo_salary)
async def process_convo_salary(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(salary=message.text)
    await message.answer(texts[lang]['ask_location'])
    await state.set_state(Form.convo_location)

@dp.message(Form.convo_location)
async def process_convo_location(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(location=message.text)
    await message.answer(texts[lang]['ask_skills'])
    await state.set_state(Form.convo_skills)

@dp.message(Form.convo_skills)
async def process_convo_skills(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(skills=message.text)
    availability_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts[lang]['button_yes'], callback_data="availability_yes")],
        [InlineKeyboardButton(text=texts[lang]['button_no'], callback_data="availability_no")]
    ])
    await message.answer(texts[lang]['ask_availability'], reply_markup=availability_keyboard)
    await state.set_state(Form.convo_availability)

@dp.callback_query(Form.convo_availability, F.data.startswith('availability_'))
async def process_convo_availability(callback: types.CallbackQuery, state: FSMContext):
    lang = await get_user_lang(state)
    choice = callback.data.split('_')[1]
    availability_text = texts[lang]['button_yes'] if choice == "yes" else texts[lang]['button_no']
    
    await state.update_data(availability=availability_text)
    await callback.message.delete_reply_markup()
    await callback.message.answer(texts[lang]['ask_contact'])
    await state.set_state(Form.convo_contact)
    await callback.answer()

@dp.message(Form.convo_contact)
async def process_convo_contact(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(contact=message.text)
    await message.answer(texts[lang]['analyzing'])

    user_data = await state.get_data()
    
    candidate_summary_text = (
        f"Vakansiya: {user_data.get('vacancy')}\n"
        f"Tajribasi: {user_data.get('experience')}\n"
        f"Maosh kutilmasi: {user_data.get('salary')}\n"
        f"Manzili: {user_data.get('location')}\n"
        f"Ko'nikmalari: {user_data.get('skills')}\n"
        f"Ishga tayyorligi: {user_data.get('availability')}\n"
        f"Aloqa: {user_data.get('contact')}"
    )
    
    prompt = texts[lang]['gemini_convo_prompt']
    full_prompt = f"{prompt}\n\nNomzod javoblari:\n{candidate_summary_text}"
    
    response = await model.generate_content_async(full_prompt)
    gemini_summary = response.text
    
    hr_notification_template = texts[lang]['hr_notification_convo']
    hr_summary_text = hr_notification_template.format(**user_data, summary=gemini_summary)

    if HR_GROUP_ID:
        await bot.send_message(HR_GROUP_ID, hr_summary_text, parse_mode="Markdown")

    await message.answer(texts[lang]['goodbye_user'])
    await state.clear()

async def main():
    if not BOT_TOKEN or not GEMINI_API_KEY:
        logging.critical("Bot tokeni yoki Gemini API kaliti topilmadi!")
        return
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())