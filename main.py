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

# --- TILLAR UCHUN LUG'AT (TO'LIQ VERSIYASI) ---
texts = {
    'uz': {
        'welcome': "Assalomu alaykum! Tilni tanlang.",
        'ask_name': "To'liq ism sharifingizni (FIO) kiriting:",
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
        'welcome': "Здравствуйте! Выберите язык.",
        'ask_name': "Введите ваше полное имя и фамилию (ФИО):",
        'ask_vacancy': "На какую вакансию вы претендуете?",
        'ask_experience': "Опишите ваш опыт работы (последнее место работы, должность, сколько лет работали).",
        'ask_salary': "Какую заработную плату вы ожидаете? (в сумах, напишите цифрой или текстом)",
        'ask_location': "Введите ваш адрес проживания (город, район).",
        'ask_skills': "Опишите ваши ключевые навыки, относящиеся к вакансии (например: Excel, 1C, Python, продажи).",
        'ask_availability': "Готовы ли вы приступить к работе в ближайшее время?",
        'button_yes': "✅ Да",
        'button_no': "❌ Нет",
        'ask_contact': "Введите ваш номер телефона для связи.",
        'goodbye_user': "Спасибо за все данные! Ваша заявка успешно принята. Мы свяжемся с вами в ближайшее время, если ваша кандидатура будет одобрена. ✅",
        'analyzing': "Данные получены. Сейчас они анализируются с помощью искусственного интеллекта, подождите немного...",
        'hr_notification_convo': """🔔 **Новый кандидат (через чат)!**

👤 **ФИО:** {name}
👨‍💼 **Вакансия:** {vacancy}
-------------------
**Ответы кандидата:**
- **Опыт:** {experience}
- **Ожидаемая зарплата:** {salary}
- **Адрес:** {location}
- **Навыки:** {skills}
- **Готовность к работе:** {availability}
- **Контакт:** {contact}
-------------------
{summary}""",
        'gemini_convo_prompt': """Ты опытный HR-менеджер. Ниже приведены ответы кандидата из чата. 
        Проанализируй эту информацию и напиши краткое и четкое заключение о кандидате на русском языке.
        Анализ должен быть в следующем формате, используй эмодзи:
        🤖 **Общее заключение:** [Заключение из 2-3 предложений на основе ответов кандидата и соответствия вакансии]
        ✨ **Сильные стороны:**
        ✅ [Первая ключевая сильная сторона, найденная в ответах]
        ✅ [Вторая ключевая сильная сторона, найденная в ответах]
        📊 **Предварительная оценка:** [Подходит / Стоит рассмотреть / Недостаточно опыта]"""
    }
}

# --- BOTNING XOTIRASI (FSM) ---
class Form(StatesGroup):
    language_selection = State()
    name = State()
    vacancy = State()
    experience = State()
    salary = State()
    location = State()
    skills = State()
    availability = State()
    contact = State()

# --- ASOSIY BOT QISMI ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def get_user_lang(state: FSMContext):
    user_data = await state.get_data()
    return user_data.get('language', 'uz')

# --- BOT SUHBATLOGIKASI ---
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
    await message.answer(texts[lang]['ask_vacancy'])
    await state.set_state(Form.vacancy)

@dp.message(Form.vacancy)
async def process_vacancy(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(vacancy=message.text)
    await message.answer(texts[lang]['ask_experience'])
    await state.set_state(Form.experience)

@dp.message(Form.experience)
async def process_experience(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(experience=message.text)
    await message.answer(texts[lang]['ask_salary'])
    await state.set_state(Form.salary)

@dp.message(Form.salary)
async def process_salary(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(salary=message.text)
    await message.answer(texts[lang]['ask_location'])
    await state.set_state(Form.location)

@dp.message(Form.location)
async def process_location(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(location=message.text)
    await message.answer(texts[lang]['ask_skills'])
    await state.set_state(Form.skills)

@dp.message(Form.skills)
async def process_skills(message: types.Message, state: FSMContext):
    lang = await get_user_lang(state)
    await state.update_data(skills=message.text)
    availability_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts[lang]['button_yes'], callback_data="availability_yes")],
        [InlineKeyboardButton(text=texts[lang]['button_no'], callback_data="availability_no")]
    ])
    await message.answer(texts[lang]['ask_availability'], reply_markup=availability_keyboard)
    await state.set_state(Form.availability)

@dp.callback_query(Form.availability, F.data.startswith('availability_'))
async def process_availability(callback: types.CallbackQuery, state: FSMContext):
    lang = await get_user_lang(state)
    choice = callback.data.split('_')[1]
    availability_text = texts[lang]['button_yes'] if choice == "yes" else texts[lang]['button_no']
    
    await state.update_data(availability=availability_text)
    await callback.message.delete_reply_markup()
    await callback.message.answer(texts[lang]['ask_contact'])
    await state.set_state(Form.contact)
    await callback.answer()

@dp.message(Form.contact)
async def process_contact(message: types.Message, state: FSMContext):
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
    hr_summary_text = hr_notification_template.format(
        name=user_data.get('name'),
        vacancy=user_data.get('vacancy'),
        experience=user_data.get('experience'),
        salary=user_data.get('salary'),
        location=user_data.get('location'),
        skills=user_data.get('skills'),
        availability=user_data.get('availability'),
        contact=user_data.get('contact'),
        summary=gemini_summary
    )

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