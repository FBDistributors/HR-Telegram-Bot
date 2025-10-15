# database.py fayli (PostgreSQL va SQLAlchemy bilan ishlash uchun to'liq yangilangan)

import os
from dotenv import load_dotenv
import logging
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, BigInteger, select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import ssl
from sqlalchemy.orm import sessionmaker, declarative_base

# .env faylini yuklab olish (database moduliga to'g'ridan-to'g'ri import qilinganda ham ishlashi uchun)
load_dotenv()

# .env faylidan ma'lumotlarni o'qish
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
# <<< O'ZGARTIRILDI: Endi bo'sh ('') qiymatlarni ham to'g'ri ishlaydi >>>
DB_PORT = os.getenv("DB_PORT") or "5432"

# Ma'lumotlar bazasiga ulanish uchun havola (URL)
# psycopg (psycopg3) async driver ishlatamiz
DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy sozlamalari
# psycopg3 async uchun SSLContext
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"sslmode": "require"}
)
Base = declarative_base()
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# --- JADVAL MODELLARI ---
class User(Base):
    __tablename__ = 'users'
    user_id = Column(BigInteger, primary_key=True, autoincrement=False)
    full_name = Column(String, nullable=False)
    username = Column(String, nullable=True)
    phone_number = Column(String, nullable=True) 
    created_at = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

class UnansweredQuestion(Base):
    __tablename__ = 'unanswered_questions'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    full_name = Column(String, nullable=False)
    question = Column(Text, nullable=False)
    lang = Column(String(2), nullable=True) # Foydalanuvchi tilini saqlash uchun
    status = Column(String, default='pending') # pending, answered
    created_at = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # database.py fayliga qo'shiladigan yangi jadval modeli

class Employee(Base):
    __tablename__ = 'employees'
    id = Column(Integer, primary_key=True)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, unique=True, nullable=False)
    position = Column(String) # Lavozimi
    telegram_id = Column(BigInteger, nullable=True) # Bog'lash uchun

    # database.py fayliga qo'shiladigan yangi jadval modeli

class ChatHistory(Base):
    __tablename__ = 'chat_history'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    role = Column(String, nullable=False)  # 'user' yoki 'assistant'
    message = Column(Text, nullable=False)
    created_at = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # database.py fayliga qo'shiladigan yangi jadval modeli



class KnowledgeBase(Base):
    __tablename__ = 'knowledge_base'
    id = Column(Integer, primary_key=True)
    topic = Column(String, nullable=False)   # Mavzu/Sarlavha
    content = Column(Text, nullable=False)    # Mazmuni
    lang = Column(String(2), nullable=False) # Til kodi ('uz' yoki 'ru')



# --- ASOSIY FUNKSIYALAR ---
async def init_db():
    """Ma'lumotlar bazasini ishga tushiradi va jadvallarni yaratadi.

    Render bepul Postgres uykudan uyg'onayotganda ulanishni yopib yuborishi mumkin,
    shuning uchun bir necha marta qayta urinish qo'shilgan.
    """
    import asyncio

    last_error: Exception | None = None
    for attempt in range(1, 6):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logging.info("PostgreSQL ma'lumotlar bazasi va jadvallari tayyor.")
            return
        except Exception as exc:  # noqa: BLE001 - bu yerda loglash uchun umumiy ushlash kerak
            last_error = exc
            wait_s = attempt * 2
            logging.warning(
                f"DB ulanishida xato (urinish {attempt}/5): {exc}. {wait_s}s kutib qayta urinaman..."
            )
            await asyncio.sleep(wait_s)

    # Agar hamon muvaffaqiyatsiz bo'lsa, asl xatoni ko'taramiz
    raise last_error  # type: ignore[misc]



async def add_user(user_id: int, full_name: str, username: str | None):
    """Yangi foydalanuvchini qo'shadi yoki ma'lumotlarini yangilaydi."""
    async with async_session_maker() as session:
        user = await session.get(User, user_id)
        if user:
            user.full_name = full_name
            user.username = username
            logging.info(f"Foydalanuvchi {user_id} ma'lumotlari yangilandi.")
        else:
            new_user = User(user_id=user_id, full_name=full_name, username=username)
            session.add(new_user)
            logging.info(f"Yangi foydalanuvchi {user_id} bazaga qo'shildi.")
        await session.commit()

async def update_user_phone_number(user_id: int, phone_number: str):
    """Foydalanuvchining telefon raqamini bazadagi yozuviga qo'shadi."""
    async with async_session_maker() as session:
        # Foydalanuvchini user_id bo'yicha topamiz
        result = await session.execute(select(User).filter(User.user_id == user_id))
        user = result.scalars().first()
        
        if user:
            user.phone_number = phone_number
            await session.commit()
            logging.info(f"Foydalanuvchi {user_id} uchun telefon raqam ({phone_number}) saqlandi.")




async def get_all_user_ids():
    """Barcha faol foydalanuvchilarning ID ro'yxatini qaytaradi."""
    async with async_session_maker() as session:
        result = await session.execute(select(User.user_id))
        return result.scalars().all()




async def add_unanswered_question(user_id: int, full_name: str, question: str, lang: str):
    """Javob berilmagan savolni bazaga qo'shadi."""
    async with async_session_maker() as session:
        new_question = UnansweredQuestion(
            user_id=user_id,
            full_name=full_name,
            question=question,
            lang=lang
        )
        session.add(new_question)
        await session.commit()
        logging.info(f"Yangi javobsiz savol bazaga qo'shildi: User ID {user_id}")


async def get_pending_questions():
    """Javob kutilayotgan barcha savollarni qaytaradi."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(UnansweredQuestion).where(UnansweredQuestion.status == 'pending')
        )
        return result.scalars().all()


async def mark_question_as_answered(question_id: int):
    """Savolni "javob berildi" deb belgilaydi."""
    async with async_session_maker() as session:
        question = await session.get(UnansweredQuestion, question_id)
        if question:
            question.status = 'answered'
            await session.commit()
            logging.info(f"Savol ID {question_id} 'answered' deb belgilandi.")


# database.py faylidagi eski is_employee o'rniga yangi funksiyalar

async def verify_employee_by_phone(phone_number: str, telegram_id: int) -> bool:
    """
    Telefon raqami orqali xodimni tekshiradi va uning Telegram ID'sini bazaga saqlaydi.
    """
    async with async_session_maker() as session:
        cleaned_number = ''.join(filter(str.isdigit, phone_number))

        result = await session.execute(
            select(Employee).filter(Employee.phone_number.like(f"%{cleaned_number}"))
        )
        employee = result.scalars().first()

        if employee:
            # Agar xodim topilsa, uning telegram_id'sini yangilaymiz
            employee.telegram_id = telegram_id
            await session.commit()
            return True
        return False


async def is_employee_by_tg_id(telegram_id: int) -> bool:
    """Berilgan Telegram ID xodimlar bazasida mavjudligini tekshiradi."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Employee).filter(Employee.telegram_id == telegram_id)
        )
        employee = result.scalars().first()
        return employee is not None
    
    # database.py fayliga qo'shiladigan yangi funksiyalar

async def add_chat_message(user_id: int, role: str, message: str):
    """Suhbatdagi yangi xabarni bazaga qo'shadi."""
    async with async_session_maker() as session:
        new_message = ChatHistory(user_id=user_id, role=role, message=message)
        session.add(new_message)
        await session.commit()

async def get_chat_history(user_id: int, limit: int = 10):
    """Foydalanuvchining oxirgi N ta suhbat tarixini qaytaradi."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.created_at.desc())
            .limit(limit)
        )
        # Natijani to'g'ri tartibda (eskidan yangiga) qaytaramiz
        return result.scalars().all()[::-1]
    

# database.py faylidagi get_knowledge_base_as_string funksiyasining yangi, to'g'ri ko'rinishi

async def get_knowledge_base_as_string(lang: str) -> str:
    """Berilgan tildagi barcha mavzularni yagona matn ko'rinishida qaytaradi."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(KnowledgeBase).filter(KnowledgeBase.lang == lang)
        )
        all_entries = result.scalars().all()

        if not all_entries:
            return "Ma'lumotlar bazasi bo'sh." if lang == 'uz' else "База знаний пуста."

        # Barcha yozuvlarni Gemini uchun tushunarli formatga keltiramiz
        formatted_kb_parts = []
        for entry in all_entries:
            # Eski ".question" va ".answer" o'rniga yangi ".topic" va ".content" ishlatamiz
            formatted_kb_parts.append(f"MAVZU: {entry.topic}\nMAZMUNI:\n{entry.content}")

        # Har bir mavzuni chiziq bilan ajratamiz
        return "\n\n---\n\n".join(formatted_kb_parts)


    # database.py fayliga qo'shiladigan yangi funksiyalar

async def add_kb_entry(topic: str, content_uz: str, content_ru: str):
    """Bilimlar bazasiga o'zbek va rus tillarida yangi mavzu qo'shadi."""
    async with async_session_maker() as session:
        # O'zbekcha yozuv
        new_entry_uz = KnowledgeBase(
            topic=topic,
            content=content_uz,
            lang='uz'
        )
        # Ruscha yozuv
        new_entry_ru = KnowledgeBase(
            topic=topic,
            content=content_ru,
            lang='ru'
        )
        session.add_all([new_entry_uz, new_entry_ru])
        await session.commit()
        logging.info(f"Yangi mavzu '{topic}' bazaga qo'shildi.")

async def get_all_kb_topics(lang: str = 'uz'):
    """Berilgan tildagi barcha mavzular ro'yxatini qaytaradi."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(KnowledgeBase.topic)
            .where(KnowledgeBase.lang == lang)
            .distinct()
        )
        return result.scalars().all()

async def delete_kb_topic(topic: str):
    """Berilgan mavzuni barcha tillarda bazadan o'chiradi."""
    async with async_session_maker() as session:
        await session.execute(
            delete(KnowledgeBase).where(KnowledgeBase.topic == topic)
        )
        await session.commit()
        logging.info(f"Mavzu '{topic}' bazadan o'chirildi.")


# database.py fayliga qo'shiladigan yangi funksiya

async def replace_kb_from_list(entries: list, lang: str):
    """
    Berilgan tildagi eski bilimlar bazasini o'chirib, o'rniga yangi ro'yxatni yozadi.
    entries - bu [{'topic': '...', 'content': '...'}, ...] ko'rinishidagi ro'yxat.
    """
    async with async_session_maker() as session:
        # 1. Shu tilga oid eski ma'lumotlarni o'chiramiz
        await session.execute(
            delete(KnowledgeBase).where(KnowledgeBase.lang == lang)
        )

        # 2. Yangi ma'lumotlarni bazaga mos obyektlarga aylantiramiz
        new_kb_objects = []
        for entry in entries:
            new_kb_objects.append(
                KnowledgeBase(
                    topic=entry['topic'],
                    content=entry['content'],
                    lang=lang
                )
            )

        # 3. Barcha yangi obyektlarni bazaga bir urinishda qo'shamiz
        if new_kb_objects:
            session.add_all(new_kb_objects)

        await session.commit()
        logging.info(f"'{lang}' tili uchun bilimlar bazasi muvaffaqiyatli yangilandi.")        