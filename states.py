# states.py

from aiogram.fsm.state import State, StatesGroup

# Asosiy bot uchun holatlar
class MainForm(StatesGroup):
    language_selection = State()
    main_menu = State()

# FAQ bo'limi uchun holatlar
class FaqForm(StatesGroup):
    verification = State()
    in_process = State()

# Ariza topshirish bo'limi uchun holatlar
class AppForm(StatesGroup):
    name = State()
    has_resume_choice = State()
    resume_upload = State()
    convo_vacancy = State()
    convo_experience = State()
    convo_salary = State()
    convo_location = State()
    convo_skills = State()
    convo_availability = State()
    convo_contact = State()

# Admin paneli uchun holatlar
class AdminForm(StatesGroup):
    waiting_for_announcement = State()


# states.py faylidagi KnowledgeBaseAdmin class'ining yangi ko'rinishi

class KnowledgeBaseAdmin(StatesGroup):
    waiting_for_kb_file = State()       # .docx faylini kutish holati
    waiting_for_lang_choice = State() # Til tanlashni kutish holati

# Taklif va shikoyatlar uchun holatlar
class SuggestionForm(StatesGroup):
    waiting_text = State()

# Hujjatlar bo'limi uchun holatlar
class DocumentForm(StatesGroup):
    verification = State()  # Xodim ekanligini tekshirish
    waiting_section = State()  # Bo'lim tanlash (namuna yoki ma'lumot)
    # Namuna hujjatlar uchun
    waiting_template_category = State()
    waiting_template_document = State()
    waiting_language = State()
    waiting_format = State()
    # Ma'lumot hujjatlari uchun
    waiting_info_category = State()  # Kategoriya tanlash (qarzdorlik, ...)
    waiting_info_document = State()
    waiting_debt_document = State()  # Qarzdorlik hujjatlar ro'yxati

# Admin: Hujjat qo'shish uchun holatlar
class AddDocumentForm(StatesGroup):
    waiting_doc_type = State()  # namuna yoki ma'lumot
    waiting_template_category = State()
    waiting_template_name_uz = State()
    waiting_template_name_ru = State()
    waiting_template_uz_pdf = State()
    waiting_template_uz_docx = State()
    waiting_template_ru_pdf = State()
    waiting_template_ru_docx = State()
    # Ma'lumot hujjat uchun
    waiting_info_category = State()  # Kategoriya tanlash (Qarzdorlik, ...)
    waiting_info_name = State()
    waiting_info_doc_type = State()  # Hisobot, Ariza...
    waiting_info_expiry = State()
    waiting_info_file = State()