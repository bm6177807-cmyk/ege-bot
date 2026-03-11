"""Мини-пробник (5 вопросов по предмету) с результатом."""
import random
from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
from data import TASKS
from keyboards import kb_mini_exam_start, kb_mini_exam_next, kb_answers, SUBJECT_NAMES
from .states import Form
from .utils import get_all_subject_tasks

router = Router()


MINI_EXAM_SIZE = 5


def _get_all_tasks(subj: str) -> list:
    return get_all_subject_tasks(subj)


@router.callback_query(F.data.startswith("mini_exam_") & ~F.data.startswith("mini_exam_start_") & ~F.data.startswith("mini_exam_next"))
async def show_mini_exam_intro(callback: CallbackQuery, state: FSMContext):
    subj = callback.data[len("mini_exam_"):]
    subj_name = SUBJECT_NAMES.get(subj, subj.capitalize())

    try:
        await callback.message.delete()
    except Exception:
        pass

    all_tasks = _get_all_tasks(subj)
    count = min(MINI_EXAM_SIZE, len(all_tasks))
    if count == 0:
        await callback.message.answer(
            f"📭 В предмете *{subj_name}* пока нет заданий для пробника.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="← Назад", callback_data=f"subj_{subj}")]
            ])
        )
        await callback.answer()
        return

    await callback.message.answer(
        f"🎯 *Мини-пробник — {subj_name}*\n\n"
        f"Ответь на {count} вопросов подряд.\n"
        f"В конце получишь результат и рекомендации.\n\n"
        f"Готов?",
        reply_markup=kb_mini_exam_start(subj),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mini_exam_start_"))
async def start_mini_exam(callback: CallbackQuery, state: FSMContext):
    subj = callback.data[len("mini_exam_start_"):]
    all_tasks = _get_all_tasks(subj)
    if not all_tasks:
        await callback.answer("Нет заданий!", show_alert=True)
        return

    selected = random.sample(all_tasks, min(MINI_EXAM_SIZE, len(all_tasks)))
    tasks_list = [t for _, t in selected]
    theme_ids = [tid for tid, _ in selected]

    await state.update_data(
        mini_exam_subj=subj,
        mini_exam_tasks=tasks_list,
        mini_exam_theme_ids=theme_ids,
        mini_exam_index=0,
        mini_exam_correct=0,
        mini_exam_start=datetime.now().isoformat(),
        mini_exam_answers=[],
    )
    await state.set_state(Form.mini_exam_question)

    try:
        await callback.message.delete()
    except Exception:
        pass

    task = tasks_list[0]
    await callback.message.answer(
        f"🎯 Вопрос 1/{len(tasks_list)}\n\n{task['text']}\n\nВыбери ответ:",
        reply_markup=kb_answers(task, hint_used=True),  # no hints in mini exam
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(Form.mini_exam_question, F.data.startswith("ans_"))
async def mini_exam_answer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tasks_list = data.get("mini_exam_tasks", [])
    index = data.get("mini_exam_index", 0)
    correct_count = data.get("mini_exam_correct", 0)
    subj = data.get("mini_exam_subj", "")
    answers = data.get("mini_exam_answers", [])

    if index >= len(tasks_list):
        await callback.answer()
        return

    task = tasks_list[index]
    parts = callback.data.split("_")
    chosen = parts[-1]
    is_correct = chosen == task["correct"]

    if is_correct:
        correct_count += 1
        feedback = "✅ Правильно!"
    else:
        feedback = f"❌ Неверно. Правильный ответ: {task['correct']}"

    answers.append({"correct": is_correct, "task_text": task["text"][:50]})

    await state.update_data(
        mini_exam_index=index + 1,
        mini_exam_correct=correct_count,
        mini_exam_answers=answers
    )

    theme_ids = data.get("mini_exam_theme_ids", [])
    theme_id = theme_ids[index] if index < len(theme_ids) else "unknown"
    db.update_theme_stats(callback.from_user.id, subj, theme_id, is_correct)
    db.update_user_stats(callback.from_user.id, is_correct)

    try:
        await callback.message.delete()
    except Exception:
        pass

    next_index = index + 1
    if next_index >= len(tasks_list):
        total = len(tasks_list)
        pct = correct_count / total * 100

        if pct >= 80:
            grade = "🏆 Отлично!"
            rec = "Ты готов к экзамену. Продолжай в том же духе!"
        elif pct >= 60:
            grade = "👍 Хорошо"
            rec = "Есть над чем поработать. Повтори слабые темы."
        elif pct >= 40:
            grade = "😐 Удовлетворительно"
            rec = "Нужно больше практики. Поработай с шпаргалками."
        else:
            grade = "😟 Нужно подтянуться"
            rec = "Начни с конспектов и базовых заданий."

        start_time = datetime.fromisoformat(data.get("mini_exam_start", datetime.now().isoformat()))
        elapsed = (datetime.now() - start_time).seconds // 60

        result_text = (
            f"🎯 *Результат мини-пробника*\n\n"
            f"{grade}\n\n"
            f"Правильных: *{correct_count}/{total}* ({pct:.0f}%)\n"
            f"Время: ~{elapsed} мин\n\n"
            f"💡 {rec}"
        )
        await callback.message.answer(
            result_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Пройти ещё раз", callback_data=f"mini_exam_start_{subj}")],
                [InlineKeyboardButton(text="← К предмету", callback_data=f"subj_{subj}")],
            ]),
            parse_mode="Markdown"
        )
        await state.set_state(Form.subject_menu)
    else:
        next_task = tasks_list[next_index]
        await callback.message.answer(
            f"{feedback}\n\n"
            f"🎯 Вопрос {next_index + 1}/{len(tasks_list)}\n\n"
            f"{next_task['text']}\n\nВыбери ответ:",
            reply_markup=kb_answers(next_task, hint_used=True),
            parse_mode="Markdown"
        )
    await callback.answer()
