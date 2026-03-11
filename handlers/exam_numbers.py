# handlers/exam_numbers.py
"""Handlers for practice-by-exam-task-number feature."""
import random

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from keyboards import (
    kb_answers,
    kb_exam_numbers,
    kb_after_exam_number_answer,
    kb_practice_menu,
    SUBJECT_NAMES,
)
from .states import Form

router = Router()


@router.callback_query(F.data.startswith("open_exam_numbers_"))
async def show_exam_numbers(callback: CallbackQuery, state: FSMContext):
    """Show the grid of exam task numbers for a subject."""
    subj = callback.data[len("open_exam_numbers_"):]
    exam_tasks = db.get_exam_task_types(subj)
    display_name = SUBJECT_NAMES.get(subj, subj.capitalize())

    if not exam_tasks:
        try:
            await callback.message.edit_text(
                f"📭 *{display_name}* — пока нет структуры заданий.\n\nСкоро добавим!",
                reply_markup=kb_practice_menu(subj),
                parse_mode="Markdown",
            )
        except Exception:
            await callback.message.answer(
                f"📭 *{display_name}* — пока нет структуры заданий.\n\nСкоро добавим!",
                reply_markup=kb_practice_menu(subj),
                parse_mode="Markdown",
            )
        await callback.answer()
        return

    try:
        await callback.message.edit_text(
            f"🔢 *{display_name}* — Практика по номеру задания\n\nВыбери номер:",
            reply_markup=kb_exam_numbers(subj, exam_tasks),
            parse_mode="Markdown",
        )
    except Exception:
        await callback.message.answer(
            f"🔢 *{display_name}* — Практика по номеру задания\n\nВыбери номер:",
            reply_markup=kb_exam_numbers(subj, exam_tasks),
            parse_mode="Markdown",
        )
    await state.update_data(subject=subj)
    await callback.answer()


@router.callback_query(F.data.startswith("examnum_"))
async def start_exam_number_practice(callback: CallbackQuery, state: FSMContext):
    """Start a practice session for a specific exam task number."""
    # callback.data format: examnum_{subj}_{exam_task_id}
    # Subjects never contain underscores, so split on the first "_" is safe even when
    # exam_task_id itself contains underscores (e.g. "task_1").
    rest = callback.data[len("examnum_"):]
    subj, exam_task_id = rest.split("_", 1)

    theme_ids = db.get_exam_task_theme_ids(subj, exam_task_id)
    if not theme_ids:
        await callback.answer("Нет тем для этого задания", show_alert=True)
        return

    # Collect all tasks from the mapped themes
    tasks = []
    for theme_id in theme_ids:
        tasks.extend(db.get_tasks_by_theme(subj, theme_id))

    # Retrieve task info for display
    exam_task_list = db.get_exam_task_types(subj)
    task_info = next((t for t in exam_task_list if t["exam_task_id"] == exam_task_id), None)
    task_number = task_info["number"] if task_info else "?"

    if not tasks:
        try:
            await callback.message.edit_text(
                f"📭 Для задания *№{task_number}* пока нет заданий в базе.\n\n"
                "Попробуй другой номер или возвращайся позже.",
                reply_markup=kb_exam_numbers(subj, exam_task_list),
                parse_mode="Markdown",
            )
        except Exception:
            await callback.message.answer(
                f"📭 Для задания *№{task_number}* пока нет заданий в базе.\n\n"
                "Попробуй другой номер или возвращайся позже.",
                reply_markup=kb_exam_numbers(subj, exam_task_list),
                parse_mode="Markdown",
            )
        await callback.answer()
        return

    task = random.choice(tasks)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        f"🔢 *Задание №{task_number}*\n\n{task['text']}",
        reply_markup=kb_answers(task, hint_used=False),
        parse_mode="Markdown",
    )

    await state.update_data(
        subject=subj,
        theme=task["theme_id"],
        task=task,
        correct=task["correct"],
        hint_used=False,
        exam_number_mode=True,
        exam_task_id=exam_task_id,
    )
    await state.set_state(Form.answering)
    await callback.answer()
