# --- TILLAR UCHUN LUG'AT (YANGI, CHIROYLI FORMAT BILAN) ---
texts = {
    'uz': {
        'welcome': "Assalomu alaykum! Tilni tanlang.",
        'ask_name': "To'liq ism-familiyangizni kiriting:",
        'ask_experience': "Rahmat! Endi tajribangiz haqida yozing (masalan, '2 yil SMM sohasida').",
        'ask_portfolio': "Ajoyib! Endi rezyumeingizni PDF yoki DOCX formatida yuboring.",
        'analyzing': "Ma'lumotlar qabul qilindi. Hozir sun'iy intellekt yordamida tahlil qilinmoqda, bir oz kuting...",
        'goodbye_user': "Arizangiz uchun rahmat! Ma'lumotlaringiz muvaffaqiyatli qabul qilindi. Agar nomzodingiz ma'qul topilsa, biz siz bilan tez orada bog'lanamiz. ✅",
        'file_error': "Iltimos, rezyumeni faqat PDF yoki DOCX formatida yuboring.",
        'hr_notification': """🔔 **Yangi nomzod!**

👤 **Ism:** {name}
📝 **Qisqa tajriba:** {experience}
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
        """
    },
    'ru': {
        'welcome': "Здравствуйте! Выберите язык.",
        'ask_name': "Введите ваше полное имя и фамилию:",
        'ask_experience': "Спасибо! Теперь опишите ваш опыт (например, '2 года в сфере SMM').",
        'ask_portfolio': "Отлично! Теперь отправьте ваше резюме в формате PDF или DOCX.",
        'analyzing': "Данные получены. Сейчас они анализируются с помощью искусственного интеллекта, подождите немного...",
        'goodbye_user': "Спасибо за вашу заявку! Ваши данные успешно приняты. Мы свяжемся с вами в ближайшее время, если ваша кандидатура будет одобрена. ✅",
        'file_error': "Пожалуйста, отправьте резюме только в формате PDF или DOCX.",
        'hr_notification': """🔔 **Новый кандидат!**

👤 **Имя:** {name}
📝 **Краткий опыт:** {experience}
-------------------
{summary}""",
        'gemini_file_prompt': """Ты опытный HR-менеджер. Приложенный PDF-файл является резюме кандидата. 
        Прочитай это резюме и напиши краткое и четкое заключение о кандидате на русском языке.
        Анализ должен быть в следующем формате, используй эмодзи для заголовков и списков:
        🤖 **Общее заключение:** [Заключение из 2-3 предложений на основе опыта, навыков и образования кандидата]
        ✨ **Сильные стороны:**
        ✅ [Первая ключевая сильная сторона, найденная в резюме]
        ✅ [Вторая ключевая сильная сторона, найденная в резюме]
        📊 **Предварительная оценка:** [Подходит / Стоит рассмотреть / Недостаточно опыта]""",
        'gemini_text_prompt': """Ты опытный HR-менеджер. Ниже приведен текст из резюме кандидата. 
        Проанализируй этот текст и напиши краткое и четкое заключение о кандидате на русском языке.
        Анализ должен быть в следующем формате, используй эмодзи для заголовков и списков:
        🤖 **Общее заключение:** [Заключение из 2-3 предложений на основе опыта, навыков и образования кандидата]
        ✨ **Сильные стороны:**
        ✅ [Первая ключевая сильная сторона, найденная в резюме]
        ✅ [Вторая ключевая сильная сторона, найденная в резюме]
        📊 **Предварительная оценка:** [Подходит / Стоит рассмотреть / Недостаточно опыта]
        
        Текст резюме:
        {resume_text}
        """
    }
}