"""Работа с ошибками по предметам."""
import random

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
from keyboards import kb_mistakes_menu, kb_mistake_review, SUBJECT_NAMES

router = Router()

_SUBJECT_NAMES = SUBJECT_NAMES


@router.callback_query(F.data.startswith("mistakes_") & ~F.data.startswith("mistakes_review_") & ~F.data.startswith("mistakes_list_"))
async def show_mistakes_menu(callback: CallbackQuery, state: FSMContext):
    subj = callback.data[len("mistakes_"):]
    user_id = callback.from_user.id
    subj_name = _SUBJECT_NAMES.get(subj, subj.capitalize())
    mistakes = db.get_subject_mistakes(user_id, subj)
    count = len(mistakes)

    try:
        await callback.message.delete()
    except Exception:
        pass

    text = f"❌ *Ошибки — {subj_name}*\n\nВсего в банке ошибок: *{count}*"
    if count == 0:
        text += "\n\nОтлично! Ошибок нет 🎉"
    await callback.message.answer(
        text,
        reply_markup=kb_mistakes_menu(subj, count > 0),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mistakes_review_"))
async def review_random_mistake(callback: CallbackQuery, state: FSMContext):
    subj = callback.data[len("mistakes_review_"):]
    user_id = callback.from_user.id
    mistakes = db.get_subject_mistakes(user_id, subj)

    if not mistakes:
        await callback.answer("Ошибок нет!", show_alert=True)
        return

    mistake = random.choice(mistakes)
    try:
        await callback.message.delete()
    except Exception:
        pass

    text = (
        f"🔁 *Повторяем ошибку*\n\n"
        f"📝 {mistake['task_text']}\n\n"
        f"✅ Правильный ответ: *{mistake['correct_answer']}*"
    )
    if mistake.get("explanation"):
        text += f"\n\n💡 {mistake['explanation']}"

    await callback.message.answer(
        text,
        reply_markup=kb_mistake_review(subj, mistake["id"]),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mistakes_list_"))
async def show_mistakes_list(callback: CallbackQuery, state: FSMContext):
    subj = callback.data[len("mistakes_list_"):]
    user_id = callback.from_user.id
    mistakes = db.get_subject_mistakes(user_id, subj)[:10]
    subj_name = _SUBJECT_NAMES.get(subj, subj.capitalize())

    if not mistakes:
        await callback.answer("Ошибок нет!", show_alert=True)
        return

    try:
        await callback.message.delete()
    except Exception:
        pass

    lines = []
    for i, m in enumerate(mistakes, 1):
        text_preview = m["task_text"][:60] + "…" if len(m["task_text"]) > 60 else m["task_text"]
        lines.append(f"{i}. {text_preview}")

    text = f"📋 *Ошибки — {subj_name}* (последние {len(mistakes)}):\n\n" + "\n\n".join(lines)

    await callback.message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Повторить случайную", callback_data=f"mistakes_review_{subj}")],
            [InlineKeyboardButton(text="← Назад", callback_data=f"mistakes_{subj}")],
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mistake_delete_"))
async def delete_mistake(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    # Format: mistake_delete_{subj}_{id}
    subj = parts[2]
    mistake_id = int(parts[3])
    user_id = callback.from_user.id
    db.remove_subject_mistake(user_id, mistake_id)
    await callback.answer("🗑 Удалено из ошибок", show_alert=False)
    mistakes = db.get_subject_mistakes(user_id, subj)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        f"✅ Ошибка удалена. Осталось: *{len(mistakes)}*",
        reply_markup=kb_mistakes_menu(subj, len(mistakes) > 0),
        parse_mode="Markdown"
    )
