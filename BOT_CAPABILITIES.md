# HR Telegram Bot Opportunities

## Overview
- Telegram orqali HR jarayonlarini avtomatlashtiruvchi, ruscha va o‘zbekcha interfeysga ega bot.
- Asinxron `aiogram` 3.x, PostgreSQL (SQLAlchemy) va Google Gemini bilan integratsiyalangan.
- Xodim/administrator rollari `employees` jadvali orqali verifikatsiya qilinadi.

```56:100:main.py
@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    await db.add_user(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username
    )
    ...
    await callback.message.answer(texts[lang]['welcome_menu'], reply_markup=keyboard)
    await state.set_state(MainForm.main_menu)
```

## Foydalanuvchi tajribasi
- **Til tanlash va menyu**: birinchi kirishda foydalanuvchi tilni tanlaydi; asosiy menyuda ariza, FAQ, hujjatlar va takliflar bo‘limlari ko‘rsatiladi.
- **Ishga qabul arizasi**: nomzodlar rezyume yuklash yoki suhbatga asoslangan savollarga javob berish orqali ma’lumot yuboradi; Gemini AI nomzod bo‘yicha HR uchun xulosa tayyorlaydi va HR guruhi bilan fayl ulashiladi.

```32:128:ariza_topshirish.py
@router.message(AppForm.name, F.text)
async def process_name(message: types.Message, state: FSMContext):
    ...
    if choice == "yes":
        await callback.message.answer(texts[lang]['prompt_for_resume'])
        await state.set_state(AppForm.resume_upload)
    elif choice == "no":
        await callback.message.answer(texts[lang]['start_convo_application'])
        await callback.message.answer(texts[lang]['ask_vacancy'])
        await state.set_state(AppForm.convo_vacancy)
```

- **FAQ yordamchisi**: faqat verifikatsiyadan o‘tgan xodimlar uchun ochiladi; telefon raqami orqali tekshiradi, bilimlar bazasi va suhbat tarixidan foydalangan holda Gemini javob qaytaradi, javob topilmasa savol HR’ga yo‘naltiriladi.
- **Hujjatlar markazi**: xodimlar uchun kategoriyalangan namuna arizalar va ma’lumot fayllarini yuboradi; telefon verifikatsiyasi talab qilinadi.
- **Mahsulot katalogi**: foydalanuvchilar `🛍️ Mahsulotlar` tugmasi orqali brend tanlaydi va mahsulot tugmasiga bosganda YouTube’dagi rolikka yo‘naltiriladi.
- **Taklif/shikoyatlar**: foydalanuvchi matn kiritadi, kerak bo‘lsa kontaktini ulashadi; HR guruhi xabarni oladi va reply orqali foydalanuvchiga javob yuborishi mumkin.

```27:111:suggestion_complaint.py
@router.message(F.text.in_([texts['uz']['suggestion_button'], texts['ru']['suggestion_button']]))
async def handle_suggestion_button(message: Message, state: FSMContext):
    ...
    if HR_GROUP_ID:
        hr_notification = f"🆕 **{texts[lang]['hr_new_suggestion']}**\n\n"
        ...
        sent_message = await bot.send_message(HR_GROUP_ID, hr_notification, parse_mode="Markdown")
        await db.save_suggestion_message(user_id, sent_message.message_id, lang, suggestion_text)
```

```1:126:product_catalog.py
@router.message(F.text.in_([texts["uz"]["products_button"], texts["ru"]["products_button"]]))
async def handle_products_entry(message: Message, state: FSMContext):
    ...
    await message.answer(
        texts[lang]["products_choose_brand"],
        reply_markup=_build_brands_keyboard(brands),
    )
...
@router.callback_query(F.data.startswith("prod_brand_"))
async def handle_brand_selection(callback: CallbackQuery, state: FSMContext):
    ...
    await callback.message.edit_text(
        f"{header_text}\\n\\n{texts[lang]['products_video_hint']}",
        reply_markup=_build_products_keyboard(products, lang),
    )
```

## Admin va HR vositalari
- **Admin menyusi**: adminlar uchun qo‘shimcha tugmalar (`📢 E'lon yuborish`, `📚 Fayl orqali yangilash`, `📄 Hujjat qo'shish`) mavjud.
- **Bilimlar bazasini yangilash**: iyerarxik `.docx` faylni yuklab, avtomatik holda `knowledge_base` jadvalini yangilaydi.
- **E’lonlar**: barcha foydalanuvchilarga ommaviy xabar yuboradi va natija bo‘yicha hisobni ko‘rsatadi.
- **Hujjat joylash**: adminlar PDF/Excel fayllarni yuklab, `documents` papkasiga saqlaydi va DB yozuvini yaratadi.
- **HR guruhi javoblari**: guruhda bot xabariga reply qilinganda, foydalanuvchiga avtomatik javob yuboriladi.

```104:206:admin_panel.py
@router.message(F.text.in_([texts['uz']['kb_update_button'], texts['ru']['kb_update_button']]))
async def handle_kb_update_button(message: Message, state: FSMContext):
    ...
    parsed_entries = parse_docx(file_bytes)
    await db.replace_kb_from_list(parsed_entries, chosen_lang)
```

## Avtomatlashtirish va integratsiyalar
- **Gemini AI**: rezyume tahlili, suhbat asosida xulosa, FAQ javoblari va javobsiz savollarni qayta ko‘rib chiqish uchun ishlatiladi.
- **Fon vazifalari**: javobsiz savollarni soat sayin tekshiradi va muddati o‘tgan hujjatlarni sutkada bir marotaba tozalaydi.

```20:97:scheduler.py
async def cleanup_expired_documents():
    while True:
        await asyncio.sleep(86400)
        await db.delete_expired_documents()
...
async def check_unanswered_questions(bot: Bot):
    while True:
        await asyncio.sleep(3600)
        pending_questions = await db.get_pending_questions()
        ...
        await bot.send_message(q.user_id, notification_text, parse_mode="Markdown")
```

## Ma’lumotlar bazasi
- `users`, `employees`, `knowledge_base`, `chat_history`, `documents`, `suggestion_messages`, `unanswered_questions`, `product_brands`, `products` jadvallari orqali foydalanuvchi faoliyati va kontent saqlanadi.
- Migratsiya ehtiyojlari `_migrate_documents_table` yordamchi funksiyasi orqali minimal darajada qoplanadi.

```44:156:database.py
class User(Base):
    __tablename__ = 'users'
    user_id = Column(BigInteger, primary_key=True, autoincrement=False)
    ...
class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True)
    name_uz = Column(String, nullable=True)
    ...
class ProductBrand(Base):
    __tablename__ = 'product_brands'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    ...
class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey("product_brands.id", ondelete="CASCADE"), nullable=False)
    ...
    product_code = Column(String, nullable=True)
    display_order = Column(String, nullable=True)
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_documents_table(conn)
```

## Sozlash va ishga tushirish
- `.env` faylida `BOT_TOKEN`, `HR_GROUP_ID`, Gemini API kaliti hamda PostgreSQL ulanish ma’lumotlari bo‘lishi kerak (`env_template.txt` dan nusxa oling).
- Kutubxonalar `pip install -r requirements.txt` orqali o‘rnatiladi.
- Botni ishga tushirish: `python main.py`; Windows’da `SelectorEventLoop` avtomatik tanlanadi.
- Fayllar `documents/templates` va `documents/info` papkalariga saqlanadi; disk va DB yo‘llari mos bo‘lishi zarur.
- Mahsulot katalogini boshqarish: `product_brands` va `products` jadvallariga yozuv qo‘shish/yangilashni DBeaver orqali PostgreSQL ma’lumotlar bazasiga ulangan holda bajarish mumkin; bot ushbu jadvallarni real vaqt rejimida o‘qiydi.


