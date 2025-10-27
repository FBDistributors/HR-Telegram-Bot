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
    waiting_category = State()  # Kategoriya tanlash
    waiting_document = State()  # Hujjat tanlash
    waiting_format = State()  # Format tanlash (PDF/DOCX)