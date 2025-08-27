# database.py fayli

import sqlite3
import logging
from datetime import datetime

# Ma'lumotlar bazasiga ulanish (agar mavjud bo'lmasa, o'zi yaratadi)
conn = sqlite3.connect('bot.db')
cursor = conn.cursor()

def init_db():
    """
    Ma'lumotlar bazasini ishga tushiradi va kerakli jadvallarni yaratadi.
    """
    try:
        # Foydalanuvchilar jadvali
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                username TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # --- YANGI JADVAL ---
        # Javob berilmagan savollar jadvali
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS unanswered_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                question TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        conn.commit()
        logging.info("Ma'lumotlar bazasi muvaffaqiyatli ishga tushirildi.")
    except Exception as e:
        logging.error(f"Ma'lumotlar bazasini ishga tushirishda xatolik: {e}")


def add_user(user_id: int, full_name: str, username: str):
    """
    Yangi foydalanuvchini bazaga qo'shadi yoki mavjud bo'lsa, ma'lumotlarini yangilaydi.
    """
    try:
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if user:
            cursor.execute('''
                UPDATE users 
                SET full_name = ?, username = ? 
                WHERE user_id = ?
            ''', (full_name, username, user_id))
            logging.info(f"Foydalanuvchi {user_id} ma'lumotlari yangilandi.")
        else:
            cursor.execute('''
                INSERT INTO users (user_id, full_name, username, created_at) 
                VALUES (?, ?, ?, ?)
            ''', (user_id, full_name, username, current_time))
            logging.info(f"Yangi foydalanuvchi {user_id} bazaga qo'shildi.")
            
        conn.commit()
    except Exception as e:
        logging.error(f"Foydalanuvchi qo'shishda xatolik: {e}")


def get_all_user_ids():
    """
    Ommaviy e'lon yuborish uchun barcha foydalanuvchilarning ID ro'yxatini qaytaradi.
    """
    try:
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        return [user[0] for user in users]
    except Exception as e:
        logging.error(f"Foydalanuvchi ID'larini olishda xatolik: {e}")
        return []

# --- YANGI FUNKSIYA ---
def add_unanswered_question(user_id: int, full_name: str, question: str):
    """
    Javob berilmagan savolni bazaga qo'shadi.
    """
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO unanswered_questions (user_id, full_name, question, created_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, full_name, question, current_time))
        conn.commit()
        logging.info(f"Yangi javobsiz savol bazaga qo'shildi: User ID {user_id}")
    except Exception as e:
        logging.error(f"Javobsiz savolni qo'shishda xatolik: {e}")


# Fayl chaqirilganda bazani ishga tushirish
if __name__ == '__main__':
    init_db()
    print("Ma'lumotlar bazasi va jadvallar yaratildi/yangilandi.")
