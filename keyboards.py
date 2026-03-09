# keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from elements import ELEMENTS
import database as db
from data import TASKS

def kb_main():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Предметы")],
            [KeyboardButton(text="🎯 Тренировка"), KeyboardButton(text="📊 Профиль")],
            [KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True
    )

def kb_cancel():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )

def kb_subjects():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Химия 🧪", callback_data="subj_chemistry")],
        [InlineKeyboardButton(text="Биология 🌿", callback_data="subj_biology")]
    ])

def kb_themes(subj: str):
    themes = TASKS.get(subj, {})
    buttons = []
    for theme_id, theme_data in themes.items():
        name = theme_data["name"]
        if len(name) > 40:
            name = name[:40] + "…"
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"theme_{subj}_{theme_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_theme_menu(user_id: int, subj: str, tid: str):
    fav_text = "⭐ Удалить из избранного" if db.is_favorite(user_id, subj, tid) else "⭐ Добавить в избранное"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Конспект по теме", callback_data=f"cons_{subj}_{tid}")],
        [InlineKeyboardButton(text="📕 PDF-конспект", callback_data=f"pdf_{subj}_{tid}")],
        [InlineKeyboardButton(text="🔍 Тестовые задания", callback_data=f"test_{subj}_{tid}")],
        [InlineKeyboardButton(text="✨ Сгенерировать задание", callback_data=f"gen_{subj}_{tid}")],
        [InlineKeyboardButton(text=fav_text, callback_data=f"fav_{subj}_{tid}")],
        [InlineKeyboardButton(text="← К списку тем", callback_data=f"back_to_themes_{subj}")]
    ])

def kb_answers(task: dict, hint_used=False):
    buttons = []
    for i, (l, o) in enumerate(zip(task["letters"], task["options"])):
        buttons.append([InlineKeyboardButton(text=f"{l}) {o}", callback_data=f"ans_{task['id']}_{l}")])
    if not hint_used:
        buttons.append([InlineKeyboardButton(text="💡 Подсказка", callback_data=f"hint_{task['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_after_answer(subj: str, theme_id: str, from_exam=False):
    if from_exam:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Далее", callback_data=f"exam_next")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Ещё задание", callback_data=f"test_{subj}_{theme_id}")],
            [InlineKeyboardButton(text="📖 Конспект по теме", callback_data=f"cons_{subj}_{theme_id}")],
            [InlineKeyboardButton(text="← В меню темы", callback_data=f"theme_{subj}_{theme_id}")]
        ])

def kb_exam_settings():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="5 вопросов", callback_data="exam_5")],
        [InlineKeyboardButton(text="10 вопросов", callback_data="exam_10")],
        [InlineKeyboardButton(text="15 вопросов", callback_data="exam_15")],
        [InlineKeyboardButton(text="20 вопросов", callback_data="exam_20")]
    ])

def kb_exam_confirm(subject):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Начать экзамен", callback_data=f"exam_start_{subject}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="exam_cancel")]
    ])

def kb_generate_confirm(subj: str, tid: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Сгенерировать", callback_data=f"generate_yes_{subj}_{tid}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"theme_{subj}_{tid}")]
    ])

def kb_periods():
    buttons = []
    for i in range(1, 8):
        buttons.append([InlineKeyboardButton(text=f"{i} период", callback_data=f"period_{i}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_elements_for_period(period):
    elements_in_period = []
    for symbol, data in ELEMENTS.items():
        if data['period'] == period:
            elements_in_period.append((symbol, data['name']))
    elements_in_period.sort(key=lambda x: ELEMENTS[x[0]]['number'])
    buttons = []
    row = []
    for i, (symbol, name) in enumerate(elements_in_period):
        row.append(InlineKeyboardButton(text=f"{symbol}", callback_data=f"element_{symbol}"))
        if len(row) == 5 or i == len(elements_in_period)-1:
            buttons.append(row)
            row = []
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_training_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Случайное задание", callback_data="random_task")],
        [InlineKeyboardButton(text="📝 Решение варианта", callback_data="exam_start")],
        [InlineKeyboardButton(text="📸 Фото-задание", callback_data="photo_instruction")],
        [InlineKeyboardButton(text="🧪 Тест на уровень", callback_data="level_test")],
        [InlineKeyboardButton(text="⚗️ Справочник реакций", callback_data="reactions")],
        [InlineKeyboardButton(text="📋 Шпаргалки", callback_data="cheatsheets")],
        [InlineKeyboardButton(text="🧪 Таблица Менделеева", callback_data="mendeleev")]
    ])

def kb_profile_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton(text="📅 Цель / Напоминание", callback_data="goal_reminder")],
        [InlineKeyboardButton(text="📌 Избранное", callback_data="my_favorites")],
        [InlineKeyboardButton(text="🔮 Прогноз баллов", callback_data="predict_score")],
        [InlineKeyboardButton(text="📉 Анализ слабых тем", callback_data="weak_analysis")]
    ])

def kb_back_to_training():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data="back_to_training")]
    ])
