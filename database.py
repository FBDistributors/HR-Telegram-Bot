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
    is_admin = Column(String, default='false') # Admin rolini belgilaydi

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


class SuggestionMessage(Base):
    __tablename__ = 'suggestion_messages'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    hr_message_id = Column(Integer, nullable=False)  # HR guruhidagi xabar ID
    user_lang = Column(String(2), nullable=False)  # Foydalanuvchi tili
    created_at = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True)
    name_uz = Column(String, nullable=True)  # O'zbek nomi
    name_ru = Column(String, nullable=True)  # Rus nomi
    category = Column(String, nullable=True)  # Kategoriya
    is_template = Column(String, default='true')  # 'true' (namuna) yoki 'false' (ma'lumot)
    uploaded_by = Column(BigInteger, nullable=True)  # Kim yukladi
    document_type = Column(String, nullable=True)  # Hisobot, Ariza, Ko'rsatma, Umumiy
    expires_at = Column(String, nullable=True)  # Amal qilish muddati
    is_active = Column(String, default='true')  # Faolmi
    # Namuna hujjatlar uchun (4 ta fayl)
    file_path_uz_pdf = Column(String, nullable=True)
    file_path_uz_docx = Column(String, nullable=True)
    file_path_ru_pdf = Column(String, nullable=True)
    file_path_ru_docx = Column(String, nullable=True)
    # Ma'lumot hujjatlar uchun (bitta fayl)
    file_path_single = Column(String, nullable=True)
    description_uz = Column(Text, nullable=True)
    description_ru = Column(Text, nullable=True)
    created_at = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))



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
                # Jadval sxemasini minimal darajada migratsiya qilish
                await _migrate_documents_table(conn)
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
async def _migrate_documents_table(conn) -> None:
    """`documents` jadvali uchun kerakli ustunlar mavjudligini tekshiradi va yo'q bo'lsa qo'shadi.

    create_all sxemani yangilamaydi, shuning uchun ishlab chiqishda oddiy IF NOT EXISTS migratsiya kifoya.
    """
    from sqlalchemy import text

    alter_statements = [
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS name_uz VARCHAR",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS name_ru VARCHAR",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS category VARCHAR",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_template VARCHAR DEFAULT 'true'",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS uploaded_by BIGINT",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS document_type VARCHAR",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS expires_at VARCHAR",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_active VARCHAR DEFAULT 'true'",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_path_uz_pdf VARCHAR",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_path_uz_docx VARCHAR",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_path_ru_pdf VARCHAR",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_path_ru_docx VARCHAR",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_path_single VARCHAR",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS description_uz TEXT",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS description_ru TEXT",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS created_at VARCHAR",
        # Employees jadvaliga admin ustuni qo'shish
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS is_admin VARCHAR DEFAULT 'false'",
    ]

    for stmt in alter_statements:
        try:
            await conn.execute(text(stmt))
        except Exception as exc:  # pragma: no cover - faqat log uchun
            logging.warning(f"Documents jadvali migratsiyasi: {exc}")




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


# --- ADMIN BOSHQARUV FUNKSIYALARI ---

async def is_admin(user_id: int) -> bool:
    """Berilgan Telegram ID admin ekanligini tekshiradi."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Employee).filter(
                Employee.telegram_id == user_id,
                Employee.is_admin == 'true'
            )
        )
        admin = result.scalars().first()
        return admin is not None


async def get_all_admins():
    """Barcha adminlar ro'yxatini qaytaradi."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Employee).filter(Employee.is_admin == 'true')
        )
        admins = result.scalars().all()
        return admins


async def set_admin_status(user_id: int, admin_status: bool):
    """Foydalanuvchining admin statusini o'zgartiradi."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Employee).filter(Employee.telegram_id == user_id)
        )
        employee = result.scalars().first()
        
        if employee:
            employee.is_admin = 'true' if admin_status else 'false'
            await session.commit()
            logging.info(f"Foydalanuvchi {user_id} admin statusi o'zgartirildi: {admin_status}")
            return True
        else:
            logging.warning(f"Foydalanuvchi {user_id} employees jadvalida topilmadi")
            return False
    
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


# --- TAKLIF/SHIKOYAT XABARLARI UCHUN YANGI FUNKSIYALAR ---

async def save_suggestion_message(user_id: int, hr_message_id: int, lang: str):
    """HR guruhiga yuborilgan taklif/shikoyat xabarining ma'lumotlarini saqlaydi."""
    async with async_session_maker() as session:
        new_suggestion_message = SuggestionMessage(
            user_id=user_id,
            hr_message_id=hr_message_id,
            user_lang=lang
        )
        session.add(new_suggestion_message)
        await session.commit()
        logging.info(f"Taklif/shikoyat xabari saqlandi: User ID {user_id}, HR Message ID {hr_message_id}")


async def get_suggestion_by_hr_message(hr_message_id: int):
    """HR guruhidagi xabar ID si orqali asl foydalanuvchi ma'lumotlarini topadi."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(SuggestionMessage).where(SuggestionMessage.hr_message_id == hr_message_id)
        )
        suggestion = result.scalars().first()
        return suggestion


# --- HUJJATLAR UCHUN FUNKSIYALAR ---

async def get_documents_by_category(category: str, lang: str):
    """Berilgan kategoriya bo'yicha hujjatlarni qaytaradi."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Document).where(Document.category == category)
        )
        documents = result.scalars().all()
        
        # Lang bo'yicha nom va tavsifni tanlaymiz
        result_docs = []
        for doc in documents:
            doc_dict = {
                'id': doc.id,
                'name': doc.name_uz if lang == 'uz' else doc.name_ru,
                'description': (doc.description_uz if lang == 'uz' else doc.description_ru) if doc.description_uz or doc.description_ru else None,
                'file_path_pdf': doc.file_path_uz_pdf if lang == 'uz' else doc.file_path_ru_pdf,
                'file_path_docx': doc.file_path_uz_docx if lang == 'uz' else doc.file_path_ru_docx,
                'category': doc.category
            }
            result_docs.append(doc_dict)
        
        return result_docs


async def get_document_by_id(doc_id: int):
    """ID bo'yicha hujjatni topadi."""
    async with async_session_maker() as session:
        document = await session.get(Document, doc_id)
        return document


async def get_template_documents(lang: str):
    """Namuna hujjatlarni qaytaradi (is_template='true')."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Document).where(
                Document.is_template == 'true',
                Document.is_active == 'true'
            )
        )
        documents = result.scalars().all()
        
        result_docs = []
        for doc in documents:
            result_docs.append({
                'id': doc.id,
                'name': doc.name_uz if lang == 'uz' else doc.name_ru,
                'file_path_pdf': doc.file_path_uz_pdf if lang == 'uz' else doc.file_path_ru_pdf,
                'file_path_docx': doc.file_path_uz_docx if lang == 'uz' else doc.file_path_ru_docx,
            })
        
        return result_docs


async def get_info_documents(lang: str):
    """Ma'lumot hujjatlarni qaytaradi (is_template='false')."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Document).where(
                Document.is_template == 'false',
                Document.is_active == 'true'
            )
        )
        documents = result.scalars().all()
        
        result_docs = []
        for doc in documents:
            result_docs.append({
                'id': doc.id,
                'name': doc.name_uz,
                'document_type': doc.document_type,
                'uploaded_by': doc.uploaded_by,
                'created_at': doc.created_at,
                'file_path': doc.file_path_single
            })
        
        return result_docs


async def add_document(
    name_uz: str, name_ru: str, is_template: str,
    file_path_uz_pdf: str = None, file_path_uz_docx: str = None,
    file_path_ru_pdf: str = None, file_path_ru_docx: str = None,
    file_path_single: str = None,
    uploaded_by: int = None, document_type: str = None,
    expires_at: str = None, category: str = None
):
    """Yangi hujjat qo'shadi."""
    async with async_session_maker() as session:
        new_doc = Document(
            name_uz=name_uz,
            name_ru=name_ru,
            is_template=is_template,
            file_path_uz_pdf=file_path_uz_pdf,
            file_path_uz_docx=file_path_uz_docx,
            file_path_ru_pdf=file_path_ru_pdf,
            file_path_ru_docx=file_path_ru_docx,
            file_path_single=file_path_single,
            uploaded_by=uploaded_by,
            document_type=document_type,
            category=category,
            expires_at=expires_at
        )
        session.add(new_doc)
        await session.commit()
        logging.info(f"Yangi hujjat bazaga qo'shildi: {name_uz}")
        return new_doc.id


async def delete_info_documents_by_type(document_type: str) -> list[str]:
    """Berilgan turdagi (is_template='false') ma'lumot hujjatlarni bazadan o'chiradi.

    Qaytaradi: o'chirilgan fayl yo'llari ro'yxati (diskdan ham o'chirish uchun qulay).
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(Document).where(
                Document.is_template == 'false',
                Document.document_type == document_type
            )
        )
        docs = result.scalars().all()

        file_paths: list[str] = []
        for doc in docs:
            if doc.file_path_single:
                file_paths.append(doc.file_path_single)
            await session.delete(doc)

        if docs:
            await session.commit()
            logging.info(
                f"Ma'lumot hujjatlari ('{document_type}') eski yozuvlari o'chirildi: {len(docs)} ta"
            )
        return file_paths


async def delete_expired_documents():
    """Muddati o'tgan hujjatlarni o'chirish."""
    from datetime import datetime, timedelta
    
    async with async_session_maker() as session:
        current_date = datetime.now()
        
        # Muddati o'tganlarni is_active=False qilish
        result = await session.execute(
            select(Document).where(
                Document.is_active == 'true',
                Document.expires_at.isnot(None)
            )
        )
        documents = result.scalars().all()
        
        expired_count = 0
        for doc in documents:
            try:
                if doc.expires_at:
                    exp_date = datetime.strptime(doc.expires_at, "%Y-%m-%d %H:%M:%S")
                    if exp_date < current_date:
                        doc.is_active = 'false'
                        expired_count += 1
            except Exception as e:
                logging.error(f"Hujjat muddati o'qishda xato: {e}")
        
        # 30 kun o'tgan is_active=False ni butunlay o'chirish
        thirty_days_ago = current_date - timedelta(days=30)
        result_old = await session.execute(
            select(Document).where(Document.is_active == 'false')
        )
        old_docs = result_old.scalars().all()
        
        deleted_count = 0
        for doc in old_docs:
            try:
                if doc.created_at:
                    created_date = datetime.strptime(doc.created_at, "%Y-%m-%d %H:%M:%S")
                    if created_date < thirty_days_ago:
                        await session.delete(doc)
                        deleted_count += 1
            except Exception as e:
                logging.error(f"Hujjatni o'chirishda xato: {e}")
        
        await session.commit()
        logging.info(f"Muddati o'tgan {expired_count} ta hujjat is_active=False qilindi. {deleted_count} ta eski hujjat o'chirildi.")


async def get_debt_documents():
    """Qarzdorlik kategoriyasiga tegishli ma'lumot hujjatlarini olish."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Document).where(
                Document.is_template == 'false',
                Document.category == 'Qarzdorlik',
                Document.is_active == 'true'
            )
        )
        documents = result.scalars().all()
        return documents        