"""Ежедневные задания по предметам."""
import random
from datetime import date

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
from data import TASKS
from keyboards import kb_daily_task, kb_answers, SUBJECT_NAMES
from .states import Form
from .utils import get_all_subject_tasks

router = Router()

_SUBJECT_NAMES = SUBJECT_NAMES

def _get_all_tasks(subj: str) -> list:
    """Возвращает все задания предмета из TASKS."""
    return get_all_subject_tasks(subj)

@router.callback_query(F.data.startswith("daily_") & ~F.data.startswith("daily_mistake_"))
async def show_daily_task(callback: CallbackQuery, state: FSMContext):
    subj = callback.data[len("daily_"):]
    user_id = callback.from_user.id
    today = date.today().isoformat()

    subj_name = _SUBJECT_NAMES.get(subj, subj.capitalize())

    all_tasks = _get_all_tasks(subj)
    if not all_tasks:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            f"📭 В предмете *{subj_name}* пока нет заданий.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="← Назад", callback_data=f"subj_{subj}")]
            ])
        )
        await callback.answer()
        return

    # Check if already have a daily task for today
    existing_task_id = db.get_subject_daily_task(user_id, subj, today)

    selected_theme_id = None
    selected_task = None

    if existing_task_id:
        for theme_id, task in all_tasks:
            if task.get("id") == existing_task_id:
                selected_theme_id = theme_id
                selected_task = task
                break

    if not selected_task:
        selected_theme_id, selected_task = random.choice(all_tasks)
        db.set_subject_daily_task(user_id, subj, today, selected_task["id"])

    try:
        await callback.message.delete()
    except Exception:
        pass

    text = (
        f"🎯 *Ежедневное задание — {subj_name}*\n\n"
        f"{selected_task['text']}\n\n"
        f"_Выбери ответ:_"
    )
    await callback.message.answer(
        text,
        reply_markup=kb_answers(selected_task, hint_used=False),
        parse_mode="Markdown"
    )
    await state.update_data(
        subject=subj,
        theme=selected_theme_id,
        task=selected_task,
        correct=selected_task["correct"],
        hint_used=False,
        from_daily=True
    )
    await state.set_state(Form.answering)
    await callback.answer()


@router.callback_query(F.data.startswith("daily_mistake_"))
async def add_daily_to_mistakes(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    # Format: daily_mistake_{subj}_{task_id}
    subj = parts[2]
    task_id = "_".join(parts[3:])

    data = await state.get_data()
    task = data.get("task", {})
    task_text = task.get("text", "Задание") if task else "Задание"
    correct_answer = task.get("correct", "") if task else ""

    user_id = callback.from_user.id
    db.add_subject_mistake(user_id, subj, task_id, task_text, correct_answer)
    await callback.answer("➕ Добавлено в ошибки!", show_alert=False)
