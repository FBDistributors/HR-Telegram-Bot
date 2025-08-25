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
