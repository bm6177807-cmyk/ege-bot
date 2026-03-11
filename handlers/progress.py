"""Прогресс по предметам."""

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
from data import TASKS
from keyboards import kb_progress_menu

router = Router()

_SUBJECT_NAMES = {
    "chemistry": "Химия",
    "biology": "Биология",
    "math": "Математика",
    "physics": "Физика",
    "informatics": "Информатика",
    "history": "История",
    "geography": "География",
    "social": "Обществознание",
    "literature": "Литература",
    "russian": "Русский язык",
    "english": "Английский",
}


@router.callback_query(F.data.startswith("progress_") & ~F.data.startswith("progress_weak_"))
async def show_progress(callback: CallbackQuery, state: FSMContext):
    subj = callback.data[len("progress_"):]
    user_id = callback.from_user.id
    subj_name = _SUBJECT_NAMES.get(subj, subj.capitalize())

    prog = db.get_subject_progress(user_id, subj)
    streak = db.get_subject_streak(user_id, subj)
    mistakes_count = db.count_subject_mistakes(user_id, subj)

    total = prog["total"]
    correct = prog["correct"]
    wrong = prog["wrong"]
    pct = (correct / total * 100) if total > 0 else 0

    try:
        await callback.message.delete()
    except Exception:
        pass

    bar_filled = int(pct / 10)
    bar = "█" * bar_filled + "░" * (10 - bar_filled)

    text = (
        f"📈 *Прогресс — {subj_name}*\n\n"
        f"Решено заданий: *{total}*\n"
        f"Правильных: *{correct}* ✅\n"
        f"Неправильных: *{wrong}* ❌\n"
        f"Точность: *{pct:.1f}%*\n"
        f"{bar}\n\n"
        f"🔥 Стрик (дней подряд): *{streak}*\n"
        f"❌ В банке ошибок: *{mistakes_count}*"
    )

    if total == 0:
        text += "\n\n_Начни решать задания, чтобы увидеть прогресс!_"

    await callback.message.answer(
        text,
        reply_markup=kb_progress_menu(subj),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("progress_weak_"))
async def show_weak_themes(callback: CallbackQuery, state: FSMContext):
    subj = callback.data[len("progress_weak_"):]
    user_id = callback.from_user.id
    subj_name = _SUBJECT_NAMES.get(subj, subj.capitalize())

    weak = db.get_subject_weak_themes(user_id, subj, limit=5)

    try:
        await callback.message.delete()
    except Exception:
        pass

    if not weak:
        text = f"📉 *Слабые темы — {subj_name}*\n\n_Реши хотя бы 3 задания по теме, чтобы увидеть анализ._"
    else:
        lines = []
        for w in weak:
            theme_name = TASKS.get(subj, {}).get(w["theme_id"], {}).get("name", w["theme_id"])
            pct = (w["correct"] / w["total"] * 100) if w["total"] > 0 else 0
            lines.append(f"• {theme_name}: {w['correct']}/{w['total']} ({pct:.0f}%)")
        text = f"📉 *Слабые темы — {subj_name}*\n\n" + "\n".join(lines)

    await callback.message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="← Назад", callback_data=f"progress_{subj}")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()
