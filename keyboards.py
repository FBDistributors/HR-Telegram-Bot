# keyboards.py fayli

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Barcha matnlar va tugmalar uchun yagona markaziy lug'at
texts = {
    'uz': {
        'welcome_lang': "Assalomu alaykum! Muloqot uchun qulay tilni tanlang.",
        'welcome_menu': "Kerakli bo'limni tanlang:",
        'apply_button': "📝 Ariza topshirish",
        'faq_button': "❓ Savol berish (FAQ)",
        'documents_button': "📄 Hujjatlar",
        'suggestion_button': "💬 Taklif va shikoyatlar",
        'start_button': "🏠 Start",
        'broadcast_button': "📢 E'lon yuborish",
        'ask_name': "To'liq ism-sharifingizni kiriting (masalan, Olimov Salim).",
        'faq_auth_prompt': "Bu bo'lim faqat kompaniya xodimlari uchun. Iltimos, shaxsingizni tasdiqlash uchun kontaktingizni yuboring.",
        'button_share_contact': "📱 Kontaktimni ulashish",
        'faq_welcome': "Kompaniyamiz haqida savolingiz bo'lsa, marhamat, yozing.",
        'faq_auth_fail': "Kechirasiz, sizda bu bo'limdan foydalanish uchun ruxsat yo'q.",
        'ai_rule_thanks': 'Agar foydalanuvchi "rahmat", "tashakkur" kabi minnatdorchilik bildirsa yoki xayrlashsa, bilimlar bazasidan foydalanma. "Arzimaydi, yana savollaringiz bo\'lsa, bemalol murojaat qiling!" kabi xushmuomala javob qaytar.',
                
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
        'ask_skills': "Lavozimga oid eng muhim ko'nikmalaringizni sanab o'ting (masalan, MS Excel, 1C, mijozlar bilan ishlash, operator).",
        'ask_availability': "Yaqin kunlarda ish boshlashga tayyormisiz?",
        'availability_yes_button': "✅ Ha",
        'availability_no_button': "❌ Yo'q",
        'ask_contact': "Siz bilan bog'lanish uchun, quyidagi tugma orqali telefon raqamingizni yuboring:",
        'application_thanks': "Barcha ma'lumotlaringiz uchun rahmat! Arizangiz qabul qilindi.",
        'analyzing_resume': "Rezyume qabul qilindi. Hozir tahlil qilinmoqda...",
        'analyzing_convo': "Ma'lumotlar qabul qilindi. Hozir tahlil qilinmoqda...",
        'file_format_error': "Iltimos, rezyumeni faqat PDF yoki DOCX formatida yuboring.",
        # keyboards.py fayli, texts['uz'] ichiga qo'shiladi

        # --- HR GURUHIGA YUBORILADIGAN MATNLAR ---
        'hr_new_candidate_resume': "Yangi nomzod (Rezyume bilan)!",
        'hr_new_candidate_convo': "Yangi nomzod (Suhbat orqali)!",
        'hr_fio': "FIO",
        'hr_vacancy': "Vakansiya",
        'hr_candidate_answers': "Nomzod javoblari",

        # keyboards.py fayli, texts['uz'] ichiga qo'shiladi

        'hr_experience': "Tajribasi",
        'hr_salary': "Maosh kutilmasi",
        'hr_location': "Manzili",
        'hr_skills': "Ko'nikmalari",
        'hr_availability': "Ishga tayyorligi",
        'hr_contact': "Aloqa",

        # --- ADMIN MATNLARI ---
        'ask_announcement': "📢 Marhamat, barcha foydalanuvchilarga yuboriladigan e'lon matnini kiriting:",
        'broadcast_started': "E'lon qabul qilindi. Tarqatish boshlandi...",
        'faq_answer_found_notification': "Assalomu alaykum, {full_name}!\n\nSiz avvalroq so'ragan savolingizga javob topildi:\n\n❓ **Sizning savolingiz:** {question}\n\n🤖 **Javob:** {answer}",
        'faq_no_answer_user': "Kechirasiz, bu savolingizga javob topa olmadim. Savolingiz mutaxassislarga yuborildi, tez orada javob berishga harakat qilamiz.",
        'faq_no_answer_hr_notification': "🔔 **Yangi javobsiz savol!**\n\n👤 **Kimdan:** {full_name}\n❓ **Savol:** {question}",
        'broadcast_report': "✅ E'lon muvaffaqiyatli yuborildi: {success_count} ta\n❌ Yuborib bo'lmadi: {fail_count} ta",
        'faq_no_answer_ai': "Kechirasiz, bu savolingizga javob topa olmadim.",

        # keyboards.py fayli, texts['uz'] ichiga qo'shiladi

        # keyboards.py fayli, texts['uz'] ichidagi o'zgarish

        # --- Bilimlar bazasini boshqarish uchun matnlar ---
        'kb_update_button': "📚 Fayl orqali yangilash",
        'ask_for_kb_file': "Iltimos, yangilangan bilimlar bazasi faylini yuboring (`kb_uz.docx` yoki `kb_ru.docx`).",
        'kb_update_success': "✅ Bilimlar bazasi muvaffaqiyatli yangilandi!",
        'kb_update_fail_format': "❌ Xatolik! Iltimos, faqat `.docx` formatidagi fayl yuboring.",
        'kb_file_received': "✅ Fayl qabul qilindi. Endi bu fayl qaysi til uchun ekanligini tanlang:",
        'kb_update_fail_parsing': "❌ Faylni o'qishda xatolik yuz berdi. Iltimos, fayl formati to'g'riligini tekshiring (sarlavhalar `=== Sarlavha ===` ko'rinishida bo'lishi kerak).",

        # --- TAKLIF VA SHIKOYATLAR BO'LIMI ---
        'ask_suggestion_text': "Taklifingiz yoki shikoyatingizni yozing:",
        'suggestion_thanks': "Xabaringiz qabul qilindi, rahmat!",
        'hr_new_suggestion': "Yangi taklif/shikoyat!",
        'hr_reply_prefix': "HR jamoasidan javob:",

        # --- HUJJATLAR BO'LIMI ---
        'documents_auth_prompt': "Bu bo'lim faqat kompaniya xodimlari uchun. Iltimos, shaxsingizni tasdiqlash uchun kontaktingizni yuboring.",
        'documents_welcome': "Hujjatlar bo'limiga xush kelibsiz!",
        'documents_auth_fail': "Kechirasiz, sizda bu bo'limdan foydalanish uchun ruxsat yo'q.",
        'documents_sections': "Quyidagi bo'limlardan birini tanlang:",
        'section_templates': "📝 Namuna hujjatlar",
        'section_info': "📄 Ma'lumot hujjatlari",
        'select_language': "Tilni tanlang:",
        'choose_format': "Formatni tanlang:",
        'format_pdf': "📕 PDF",
        'format_docx': "📘 Word (DOCX)",
        'back_to_sections': "⬅️ Bo'limlarga qaytish",
        'back_to_documents': "⬅️ Hujjatlarga qaytish",
        'uploaded_by': "Yuklagan: {name}",
        'uploaded_at': "Sana: {date}",
        'doc_type': "Turi: {type}",
        'add_document_button': "📄 Hujjat qo'shish",
        'ask_doc_type': "Hujjatning turini tanlang:",
        'doc_type_template': "📝 Namuna hujjat",
        'doc_type_info': "📄 Ma'lumot hujjati",
        'ask_template_name_uz': "O'zbek tilidagi hujjat nomini kiriting:",
        'ask_template_name_ru': "Rus tilidagi hujjat nomini kiriting:",
        'ask_template_uz_pdf': "O'zbek tilidagi PDF faylni yuboring:",
        'ask_template_uz_docx': "O'zbek tilidagi Word (DOCX) faylni yuboring:",
        'ask_template_ru_pdf': "Rus tilidagi PDF faylni yuboring:",
        'ask_template_ru_docx': "Rus tilidagi Word (DOCX) faylni yuboring:",
        'ask_info_name': "Ma'lumot hujjati nomini kiriting:",
        'ask_info_type': "Hujjat turini tanlang:",
        'info_type_report': "📊 Hisobot",
        'info_type_application': "📝 Ariza",
        'info_type_instruction': "📋 Ko'rsatma",
        'info_type_general': "📁 Umumiy",
        'ask_info_expiry': "Amal qilish muddatini kiriting (masalan, 2024-12-31 yoki bo'sh qoldiring):",
        'ask_info_file': "Ma'lumot hujjati faylini yuboring:",
        'doc_added_success': "✅ Hujjat muvaffaqiyatli qo'shildi!",
        'doc_add_cancelled': "❌ Hujjat qo'shish bekor qilindi.",
        'doc_add_error': "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",

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
        'documents_button': "📄 Документы",
        'suggestion_button': "💬 Предложения и жалобы",
        'start_button': "🏠 Start",
        'broadcast_button': "📢 Отправить объявление",
        'ask_name': "Введите Ваши полные имя и фамилию (например, Салимов Олим).",
        'faq_auth_prompt': "Этот раздел предназначен только для сотрудников компании. Пожалуйста, отправьте свой контакт для подтверждения личности.",
        'button_share_contact': "📱 Поделиться моим контактом",
        'faq_welcome': "Если у вас есть вопросы о нашей компании, пожалуйста, напишите.",
        'faq_auth_fail': "К сожалению, у вас нет доступа к этому разделу.",
        'ai_rule_thanks': 'Если пользователь благодарит (например, "спасибо") или прощается, не используй базу знаний. Ответь вежливо, например: "Пожалуйста! Если у вас будут еще вопросы, обращайтесь."',

        'ask_has_resume': "Спасибо. У вас есть готовое резюме для продолжения заявки?",
        'has_resume_yes_button': "✅ Да, отправить резюме",
        'has_resume_no_button': "❌ Нет, пройти собеседование",
        'prompt_for_resume': "Пожалуйста, отправьте ваше резюме в формате PDF или DOCX.",
        'start_convo_application': "Ничего страшного! Вместо этого, давайте получим информацию о вас через несколько вопросов.",
        'ask_vacancy': "Введите название вакансии, на которую Вы претендуете (например, Бухгалтер).",
        'ask_experience': "Опишите ваш опыт работы (последнее место работы, должность, сколько лет работали).",
        'ask_salary': "Укажите ваши ожидания по заработной плате (в сумах).",
        'ask_location': "Введите ваш адрес проживания (город, район).",
        'ask_skills': "Перечислите ваши ключевые навыки для данной позиции (например, MS Excel, 1C, работа с клиентами, продажи).",
        'ask_availability': "Готовы ли вы приступить к работе в ближайшее время?",
        'availability_yes_button': "✅ Да",
        'availability_no_button': "❌ Нет",
        'ask_contact': "Для связи, пожалуйста, отправьте ваш номер телефона с помощью кнопки ниже:",
        'application_thanks': "Спасибо за все данные! Ваша заявка принята.",
        'analyzing_resume': "Резюме получено. Сейчас оно анализируется...",
        'analyzing_convo': "Данные получены. Сейчас они анализируются...",
        'file_format_error': "Пожалуйста, отправьте резюме только в формате PDF или DOCX.",
        # keyboards.py fayli, texts['ru'] ichiga qo'shiladi

        # --- ТЕКСТЫ ДЛЯ ОТПРАВКИ В HR-ГРУППУ ---
        'hr_new_candidate_resume': "Новый кандидат (с резюме)!",
        'hr_new_candidate_convo': "Новый кандидат (по итогам чата)!",
        'hr_fio': "ФИО",
        'hr_vacancy': "Вакансия",
        'hr_candidate_answers': "Ответы кандидата",

        # keyboards.py fayli, texts['ru'] ichiga qo'shiladi

        'hr_experience': "Опыт работы",
        'hr_salary': "Ожидания по зарплате",
        'hr_location': "Местоположение",
        'hr_skills': "Навыки",
        'hr_availability': "Готовность к работе",
        'hr_contact': "Контакт",

        'ask_announcement': "📢 Пожалуйста, введите текст объявления для отправки всем пользователям:",
        'broadcast_started': "Объявление принято. Начинаю рассылку...",
        'faq_answer_found_notification': "Здравствуйте, {full_name}!\n\nНайден ответ на ваш предыдущий вопрос:\n\n❓ **Ваш вопрос:** {question}\n\n🤖 **Ответ:** {answer}",
        'faq_no_answer_user': "Извините, я не смог найти ответ на ваш вопрос. Ваш вопрос был направлен специалистам, мы постараемся ответить в ближайшее время.",
        'faq_no_answer_hr_notification': "🔔 **Новый вопрос без ответа!**\n\n👤 **От кого:** {full_name}\n❓ **Вопрос:** {question}",
        'broadcast_report': "✅ Успешно отправлено: {success_count}\n❌ Не удалось отправить: {fail_count}",
        'faq_no_answer_ai': "К сожалению, я не могу ответить на ваш вопрос.",

        # keyboards.py fayli, texts['ru'] ichidagi o'zgarish

        # --- Тексты для управления базой знаний ---
        'kb_update_button': "📚 Обновить через файл",
        'ask_for_kb_file': "Пожалуйста, отправьте обновленный файл базы знаний (`kb_uz.docx` или `kb_ru.docx`).",
        'kb_update_success': "✅ База знаний успешно обновлена!",
        'kb_update_fail_format': "❌ Ошибка! Пожалуйста, отправляйте файл только в формате `.docx`.",
        'kb_file_received': "✅ Файл получен. Теперь выберите, для какого языка этот файл:",
        'kb_update_fail_parsing': "❌ Произошла ошибка при чтении файла. Пожалуйста, проверьте правильность формата файла (заголовки должны быть в виде `=== Заголовок ===`).",

        # --- РАЗДЕЛ ПРЕДЛОЖЕНИЙ И ЖАЛОБ ---
        'ask_suggestion_text': "Напишите ваше предложение или жалобу:",
        'suggestion_thanks': "Ваше сообщение принято, спасибо!",
        'hr_new_suggestion': "Новое предложение/жалоба!",
        'hr_reply_prefix': "Ответ от HR команды:",

        # --- РАЗДЕЛ ДОКУМЕНТОВ ---
        'documents_auth_prompt': "Этот раздел предназначен только для сотрудников компании. Пожалуйста, отправьте свой контакт для подтверждения личности.",
        'documents_welcome': "Добро пожаловать в раздел документов!",
        'documents_auth_fail': "К сожалению, у вас нет доступа к этому разделу.",
        'documents_sections': "Выберите один из следующих разделов:",
        'section_templates': "📝 Шаблоны документов",
        'section_info': "📄 Информационные документы",
        'select_language': "Выберите язык:",
        'choose_format': "Выберите формат:",
        'format_pdf': "📕 PDF",
        'format_docx': "📘 Word (DOCX)",
        'back_to_sections': "⬅️ Вернуться к разделам",
        'back_to_documents': "⬅️ Вернуться к документам",
        'uploaded_by': "Загрузил: {name}",
        'uploaded_at': "Дата: {date}",
        'doc_type': "Тип: {type}",
        'add_document_button': "📄 Добавить документ",
        'ask_doc_type': "Выберите тип документа:",
        'doc_type_template': "📝 Шаблон документа",
        'doc_type_info': "📄 Информационный документ",
        'ask_template_name_uz': "Введите название документа на узбекском языке:",
        'ask_template_name_ru': "Введите название документа на русском языке:",
        'ask_template_uz_pdf': "Отправьте PDF файл на узбекском языке:",
        'ask_template_uz_docx': "Отправьте Word (DOCX) файл на узбекском языке:",
        'ask_template_ru_pdf': "Отправьте PDF файл на русском языке:",
        'ask_template_ru_docx': "Отправьте Word (DOCX) файл на русском языке:",
        'ask_info_name': "Введите название информационного документа:",
        'ask_info_type': "Выберите тип документа:",
        'info_type_report': "📊 Отчет",
        'info_type_application': "📝 Заявка",
        'info_type_instruction': "📋 Инструкция",
        'info_type_general': "📁 Общий",
        'ask_info_expiry': "Введите срок действия (например, 2024-12-31 или оставьте пустым):",
        'ask_info_file': "Отправьте файл информационного документа:",
        'doc_added_success': "✅ Документ успешно добавлен!",
        'doc_add_cancelled': "❌ Добавление документа отменено.",
        'doc_add_error': "❌ Произошла ошибка. Пожалуйста, попробуйте еще раз.",

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
            [KeyboardButton(text=texts[lang]['apply_button']), KeyboardButton(text=texts[lang]['faq_button'])],
            [KeyboardButton(text=texts[lang]['documents_button']), KeyboardButton(text=texts[lang]['suggestion_button'])]
        ],
        resize_keyboard=True
    )

def get_admin_keyboard(lang: str = 'uz'):
    """Admin uchun menyu klaviaturasini qaytaradi."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=texts[lang]['apply_button']), KeyboardButton(text=texts[lang]['faq_button'])],
            [KeyboardButton(text=texts[lang]['broadcast_button']), KeyboardButton(text=texts[lang]['start_button'])]
        ],
        resize_keyboard=True
    )

# keyboards.py fayliga qo'shiladigan yangi funksiyalar

def get_admin_main_keyboard(lang: str = 'uz'):
    """Asosiy admin menyusini qaytaradi."""
    return ReplyKeyboardMarkup(
        keyboard=[
            # Oddiy foydalanuvchi tugmalarini ham qo'shamiz
            [KeyboardButton(text=texts[lang]['apply_button']), KeyboardButton(text=texts[lang]['faq_button'])],
            [KeyboardButton(text=texts[lang]['documents_button']), KeyboardButton(text=texts[lang]['suggestion_button'])],
            # Admin tugmalari
            [KeyboardButton(text=texts[lang]['kb_update_button']), KeyboardButton(text=texts[lang]['broadcast_button'])],
            [KeyboardButton(text=texts[lang]['add_document_button'])],
        ],
        resize_keyboard=True
    )


    