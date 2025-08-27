# keyboards.py fayli

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Barcha matnlar va tugmalar uchun yagona markaziy lug'at
texts = {
    'uz': {
        'welcome_lang': "Assalomu alaykum! Muloqot uchun qulay tilni tanlang.",
        'welcome_menu': "Kerakli bo'limni tanlang:",
        'apply_button': "📝 Ariza topshirish",
        'faq_button': "❓ Savol berish (FAQ)",
        'broadcast_button': "📢 E'lon yuborish",
        'ask_name': "To'liq ism-sharifingizni kiriting (masalan, Olimov Salim).",
        'faq_auth_prompt': "Bu bo'lim faqat kompaniya xodimlari uchun. Iltimos, shaxsingizni tasdiqlash uchun kontaktingizni yuboring.",
        'button_share_contact': "📱 Kontaktimni ulashish",
        'faq_welcome': "Kompaniyamiz haqida savolingiz bo'lsa, marhamat, yozing.",
        'faq_auth_fail': "Kechirasiz, sizda bu bo'limdan foydalanish uchun ruxsat yo'q.",
        
        # --- ARIZA BO'LIMI UCHUN TO'LIQ MATNLAR ---
        'ask_has_resume': "Rahmat. Arizani davom ettirish uchun tayyor rezyumeingiz mavjudmi?",
        'has_resume_yes_button': "✅ Ha, rezyume yuborish",
        'has_resume_no_button': "❌ Yo'q, suhbatdan o'tish",
        'prompt_for_resume': "Marhamat, rezyumeni PDF yoki DOCX formatida yuboring.",
        'start_convo_application': "Hechqisi yo'q! Keling, o'rniga bir nechta savollar orqali siz haqingizda ma'lumot olamiz.",
        'ask_vacancy': "Murojaat qilayotgan vakansiya nomini kiriting (masalan, Buxgalter).",
        'ask_experience': "Ish tajribangiz haqida yozing (oxirgi ish joyingiz, lavozimingiz, necha yil ishlaganingiz).",
        'ask_salary': "Oylik maosh bo'yicha kutilmalaringizni kiriting (so'mda).",
        'ask_location': "Yashash manzilingizni kiriting (shahar, tuman).",
        'ask_skills': "Lavozimga oid eng muhim ko'nikmalaringizni sanab o'ting.",
        'ask_availability': "Yaqin kunlarda ish boshlashga tayyormisiz?",
        'availability_yes_button': "✅ Ha",
        'availability_no_button': "❌ Yo'q",
        'ask_contact': "Siz bilan bog'lanish uchun, quyidagi tugma orqali telefon raqamingizni yuboring:",
        'application_thanks': "Barcha ma'lumotlaringiz uchun rahmat! Arizangiz qabul qilindi.",
        'analyzing_resume': "Rezyume qabul qilindi. Hozir tahlil qilinmoqda...",
        'analyzing_convo': "Ma'lumotlar qabul qilindi. Hozir tahlil qilinmoqda...",
        'file_format_error': "Iltimos, rezyumeni faqat PDF yoki DOCX formatida yuboring.",

        # --- ADMIN MATNLARI ---
        'ask_announcement': "📢 Marhamat, barcha foydalanuvchilarga yuboriladigan e'lon matnini kiriting:",
        'broadcast_started': "E'lon qabul qilindi. Tarqatish boshlandi...",
        'faq_answer_found_notification': "Assalomu alaykum, {full_name}!\n\nSiz avvalroq so'ragan savolingizga javob topildi:\n\n❓ **Sizning savolingiz:** {question}\n\n🤖 **Javob:** {answer}",
        'faq_no_answer_user': "Kechirasiz, bu savolingizga javob topa olmadim. Savolingiz mutaxassislarga yuborildi, tez orada javob berishga harakat qilamiz.",
        'faq_no_answer_hr_notification': "🔔 **Yangi javobsiz savol!**\n\n👤 **Kimdan:** {full_name}\n❓ **Savol:** {question}",
        'broadcast_report': "✅ E'lon muvaffaqiyatli yuborildi: {success_count} ta\n❌ Yuborib bo'lmadi: {fail_count} ta",
        'faq_no_answer_ai': "Kechirasiz, bu savolingizga javob topa olmadim.",

        # --- SUN'IY INTELLEKT UCHUN PROMPTLAR (TO'LDIRILDI) ---
        'gemini_convo_prompt': """Sen tajribali HR-menejersan. Quyida nomzodning suhbat orqali bergan javoblari keltirilgan.
Ushbu ma'lumotlarni tahlil qilib, nomzod haqida o'zbek tilida, lotin alifbosida qisqacha va aniq xulosa yoz.
Tahlil quyidagi formatda bo'lsin, emoji'lardan foydalan:
🤖 **Umumiy xulosa:** [Nomzodning javoblari va vakansiyaga mosligi asosida 2-3 gaplik xulosa]
✨ **Kuchli tomonlari:**
✅ [Suhbatdan topilgan birinchi kuchli jihat]
✅ [Suhbatdan topilgan ikkinchi kuchli jihat]
📊 **Dastlabki baho:** [Mos keladi / O'ylab ko'rish kerak / Tajribasi kam]
    

Nomzod javoblari:
{candidate_summary}""",

        'gemini_file_prompt': """Sen tajribali HR-menejersan. Ilova qilingan fayl nomzodning rezyumesi hisoblanadi.
Ushbu rezyumeni o'qib chiqib, nomzod haqida o'zbek tilida, lotin alifbosida qisqacha va aniq xulosa yoz.
Tahlil quyidagi formatda bo'lsin, sarlavhalar va ro'yxatlar uchun emoji'lardan foydalan:
🤖 **Umumiy xulosa:** [Nomzodning tajribasi, ko'nikmalari va ma'lumotlari asosida 2-3 gaplik xulosa]
✨ **Kuchli tomonlari:**
✅ [Rezyumedan topilgan birinchi kuchli jihat]
✅ [Rezyumedan topilgan ikkinchi kuchli jihat]
📊 **Dastlabki baho:** [Mos keladi / O'ylab ko'rish kerak / Tajribasi kam]""",
    },
    'ru': {
        'welcome_lang': "Здравствуйте! Пожалуйста, выберите удобный язык для общения.",
        'welcome_menu': "Пожалуйста, выберите нужный раздел:",
        'apply_button': "📝 Подать заявку",
        'faq_button': "❓ Задать вопрос (FAQ)",
        'broadcast_button': "📢 Отправить объявление",
        'ask_name': "Введите Ваши полные имя и фамилию (например, Салимов Олим).",
        'faq_auth_prompt': "Этот раздел предназначен только для сотрудников компании. Пожалуйста, отправьте свой контакт для подтверждения личности.",
        'button_share_contact': "📱 Поделиться моим контактом",
        'faq_welcome': "Если у вас есть вопросы о нашей компании, пожалуйста, напишите.",
        'faq_auth_fail': "К сожалению, у вас нет доступа к этому разделу.",

        'ask_has_resume': "Спасибо. У вас есть готовое резюме для продолжения заявки?",
        'has_resume_yes_button': "✅ Да, отправить резюме",
        'has_resume_no_button': "❌ Нет, пройти собеседование",
        'prompt_for_resume': "Пожалуйста, отправьте ваше резюме в формате PDF или DOCX.",
        'start_convo_application': "Ничего страшного! Вместо этого, давайте получим информацию о вас через несколько вопросов.",
        'ask_vacancy': "Введите название вакансии, на которую Вы претендуете (например, Бухгалтер).",
        'ask_experience': "Опишите ваш опыт работы (последнее место работы, должность, сколько лет работали).",
        'ask_salary': "Укажите ваши ожидания по заработной плате (в сумах).",
        'ask_location': "Введите ваш адрес проживания (город, район).",
        'ask_skills': "Перечислите ваши ключевые навыки для данной позиции.",
        'ask_availability': "Готовы ли вы приступить к работе в ближайшее время?",
        'availability_yes_button': "✅ Да",
        'availability_no_button': "❌ Нет",
        'ask_contact': "Для связи, пожалуйста, отправьте ваш номер телефона с помощью кнопки ниже:",
        'application_thanks': "Спасибо за все данные! Ваша заявка принята.",
        'analyzing_resume': "Резюме получено. Сейчас оно анализируется...",
        'analyzing_convo': "Данные получены. Сейчас они анализируются...",
        'file_format_error': "Пожалуйста, отправьте резюме только в формате PDF или DOCX.",

        'ask_announcement': "📢 Пожалуйста, введите текст объявления для отправки всем пользователям:",
        'broadcast_started': "Объявление принято. Начинаю рассылку...",
        'faq_answer_found_notification': "Здравствуйте, {full_name}!\n\nНайден ответ на ваш предыдущий вопрос:\n\n❓ **Ваш вопрос:** {question}\n\n🤖 **Ответ:** {answer}",
        'faq_no_answer_user': "Извините, я не смог найти ответ на ваш вопрос. Ваш вопрос был направлен специалистам, мы постараемся ответить в ближайшее время.",
        'faq_no_answer_hr_notification': "🔔 **Новый вопрос без ответа!**\n\n👤 **От кого:** {full_name}\n❓ **Вопрос:** {question}",
        'broadcast_report': "✅ Успешно отправлено: {success_count}\n❌ Не удалось отправить: {fail_count}",
        'faq_no_answer_ai': "К сожалению, я не могу ответить на ваш вопрос.",

        # --- SUN'IY INTELLEKT UCHUN PROMPTLAR (TO'LDIRILDI) ---
        'gemini_convo_prompt': """Ты опытный HR-менеджер. Ниже приведены ответы кандидата из чата.
Проанализируй эту информацию и напиши краткое и четкое заключение о кандидате на русском языке.
Анализ должен быть в следующем формате, используй эмодзи:
🤖 **Общее заключение:** [Заключение из 2-3 предложений на основе ответов кандидата и соответствия вакансии]
✨ **Сильные стороны:**
✅ [Первая ключевая сильная сторона, найденная в ответах]
✅ [Вторая ключевая сильная сторона, найденная в ответах]
📊 **Предварительная оценка:** [Подходит / Стоит рассмотреть / Недостаточно опыта]

Ответы кандидата:
{candidate_summary}""",
        'gemini_file_prompt': """Ты опытный HR-менеджер. Приложенный файл является резюме кандидата.
Прочитай это резюме и напиши краткое и четкое заключение о кандидате на русском языке.
Анализ должен быть в следующем формате, используй эмодзи для заголовков и списков:
🤖 **Общее заключение:** [Заключение из 2-3 предложений на основе опыта, навыков и образования кандидата]
✨ **Сильные стороны:**
✅ [Первая ключевая сильная сторона, найденная в резюме]
✅ [Вторая ключевая сильная сторона, найденная в резюме]
📊 **Предварительная оценка:** [Подходит / Стоит рассмотреть / Недостаточно опыта]""",

    }
}

def get_user_keyboard(lang: str = 'uz'):
    """Oddiy foydalanuvchi uchun menyu klaviaturasini qaytaradi."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts[lang]['apply_button'])],
            [KeyboardButton(text=texts[lang]['faq_button'])],
        ],
        resize_keyboard=True
    )

def get_admin_keyboard(lang: str = 'uz'):
    """Admin uchun menyu klaviaturasini qaytaradi."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts[lang]['apply_button']), KeyboardButton(text=texts[lang]['faq_button'])],
            [KeyboardButton(text=texts[lang]['broadcast_button'])],
        ],
        resize_keyboard=True
    )
