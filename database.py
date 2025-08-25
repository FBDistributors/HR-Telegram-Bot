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
    Bu funksiya bot ishga tushganda bir marta chaqirilishi kerak.
    """
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                username TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        conn.commit()
        logging.info("Ma'lumotlar bazasi muvaffaqiyatli ishga tushirildi va 'users' jadvali tayyor.")
    except Exception as e:
        logging.error(f"Ma'lumotlar bazasini ishga tushirishda xatolik: {e}")


def add_user(user_id: int, full_name: str, username: str):
    """
    Yangi foydalanuvchini bazaga qo'shadi yoki mavjud bo'lsa, ma'lumotlarini yangilaydi.
    """
    try:
        # Foydalanuvchi bazada bor yoki yo'qligini tekshirish
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if user:
            # Agar foydalanuvchi mavjud bo'lsa, uning ismini yangilaymiz (o'zgargan bo'lishi mumkin)
            cursor.execute('''
                UPDATE users 
                SET full_name = ?, username = ? 
                WHERE user_id = ?
            ''', (full_name, username, user_id))
            logging.info(f"Foydalanuvchi {user_id} ma'lumotlari yangilandi.")
        else:
            # Agar foydalanuvchi yangi bo'lsa, uni bazaga qo'shamiz
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
        # Natijani oddiy ro'yxat ko'rinishiga o'tkazish, masalan: [123, 456, 789]
        return [user[0] for user in users]
    except Exception as e:
        logging.error(f"Foydalanuvchi ID'larini olishda xatolik: {e}")
        return []

# Fayl chaqirilganda bazani ishga tushirish
if __name__ == '__main__':
    # Bu qism faylni to'g'ridan-to'g'ri ishga tushirganda ishlaydi (test uchun)
    init_db()
    print("Ma'lumotlar bazasi va jadval yaratildi.")

