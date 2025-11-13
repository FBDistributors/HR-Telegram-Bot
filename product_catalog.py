import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import database as db
from keyboards import texts
from states import MainForm

router = Router()


async def get_user_lang(state: FSMContext) -> str:
    data = await state.get_data()
    return data.get("language", "uz")


def _build_brands_keyboard(brands: list[db.ProductBrand]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=brand.name, callback_data=f"prod_brand_{brand.id}")]
        for brand in brands
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_products_keyboard(products: list[db.Product], lang: str) -> InlineKeyboardMarkup:
    keyboard_rows = [
        [InlineKeyboardButton(text=product.name, url=product.youtube_url)]
        for product in products
    ]
    keyboard_rows.append(
        [InlineKeyboardButton(text=texts[lang]["products_back_to_brands"], callback_data="prod_back_brands")]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


@router.message(F.text.in_([texts["uz"]["products_button"], texts["ru"]["products_button"]]))
async def handle_products_entry(message: Message, state: FSMContext):
    lang = await get_user_lang(state)

    try:
        brands = await db.get_all_product_brands()
    except Exception as exc:
        logging.error(f"Mahsulot brendlarini olishda xato: {exc}")
        await message.answer("❌ Ma'lumotlarni olishda xatolik yuz berdi. Keyinroq urinib ko'ring.")
        return

    if not brands:
        await message.answer(texts[lang]["products_no_brands"])
        return

    await message.answer(
        texts[lang]["products_choose_brand"],
        reply_markup=_build_brands_keyboard(brands),
    )
    await state.set_state(MainForm.main_menu)


@router.callback_query(F.data.startswith("prod_brand_"))
async def handle_brand_selection(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(state)
    try:
        brand_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer("Xatolik.", show_alert=True)
        return

    try:
        brand = await db.get_product_brand(brand_id)
    except Exception as exc:
        logging.error(f"Brendni olishda xato (ID={brand_id}): {exc}")
        await callback.answer("Xatolik yuz berdi.", show_alert=True)
        return

    if not brand:
        await callback.answer("Brend topilmadi.", show_alert=True)
        return

    try:
        products = await db.get_products_by_brand(brand_id)
    except Exception as exc:
        logging.error(f"Mahsulotlarni olishda xato (brand_id={brand_id}): {exc}")
        await callback.answer("Xatolik yuz berdi.", show_alert=True)
        return

    header_text = texts[lang]["products_list_header"].format(brand=brand.name)

    if not products:
        await callback.message.edit_text(
            f"{header_text}\n\n{texts[lang]['products_no_products']}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=texts[lang]["products_back_to_brands"], callback_data="prod_back_brands")]
                ]
            ),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"{header_text}\n\n{texts[lang]['products_video_hint']}",
        reply_markup=_build_products_keyboard(products, lang),
    )
    await callback.answer()


@router.callback_query(F.data == "prod_back_brands")
async def handle_back_to_brands(callback: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(state)
    try:
        brands = await db.get_all_product_brands()
    except Exception as exc:
        logging.error(f"Brendlar ro'yxatini qayta olishda xato: {exc}")
        await callback.answer("Xatolik yuz berdi.", show_alert=True)
        return

    if not brands:
        await callback.message.edit_text(texts[lang]["products_no_brands"])
        await callback.answer()
        return

    await callback.message.edit_text(
        texts[lang]["products_choose_brand"],
        reply_markup=_build_brands_keyboard(brands),
    )
    await callback.answer()

