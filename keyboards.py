# keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from elements import ELEMENTS
import database as db
from data import TASKS

# ========== ОСНОВНАЯ КЛАВИАТУРА ==========
def kb_main():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📸 Разбор по фото"), KeyboardButton(text="📚 Предметы")],
            [KeyboardButton(text="📊 Профиль"), KeyboardButton(text="🌟 Купить премиум")]
        ],
        resize_keyboard=True
    )

def kb_cancel():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )

# ========== ПРЕДМЕТЫ И ТЕМЫ ==========
def kb_subjects():
    display_names = {
        "chemistry": "Химия 🧪",
        "biology": "Биология 🌿",
        "math": "Математика 📐",
        "physics": "Физика ⚡",
        "informatics": "Информатика 💻",
        "history": "История 📜",
        "geography": "География 🌍",
        "social": "Обществознание 🏛️",
        "literature": "Литература 📖",
        "russian": "Русский язык 🇷🇺"
    }
    buttons = []
    for subject_key in TASKS.keys():
        button_text = display_names.get(subject_key, subject_key.capitalize())
        buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"subj_{subject_key}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def kb_subject_menu(subj: str):
    """Клавиатура меню предмета."""
    buttons = [
        [InlineKeyboardButton(text="🎲 Случайное задание", callback_data=f"subj_random_{subj}")],
        [InlineKeyboardButton(text="📝 Экзамен", callback_data=f"subj_exam_{subj}")],
        [InlineKeyboardButton(text="📸 Фото-задание", callback_data=f"subj_photo_{subj}")],
        [InlineKeyboardButton(text="🧪 Тест на уровень", callback_data=f"subj_level_{subj}")],
        [InlineKeyboardButton(text="📋 Шпаргалки", callback_data=f"subj_cheat_{subj}")],
        [InlineKeyboardButton(text="📚 Выбрать тему", callback_data=f"subj_themes_{subj}")]
    ]
    if subj == "chemistry":
        buttons.append([InlineKeyboardButton(text="⚗️ Справочник реакций", callback_data=f"subj_reactions_{subj}")])
        buttons.append([InlineKeyboardButton(text="🧪 Таблица Менделеева", callback_data=f"subj_mendeleev_{subj}")])
    _TOOL_SUBJECTS = {"math", "physics", "geography", "history", "informatics", "biology"}
    if subj in _TOOL_SUBJECTS:
        buttons.append([InlineKeyboardButton(text="🧰 Инструменты", callback_data=f"tool_{subj}")])
    buttons.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

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

# ========== ОТВЕТЫ НА ЗАДАНИЯ ==========
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

# ========== ЭКЗАМЕН ==========
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

# ========== ГЕНЕРАЦИЯ ЗАДАНИЙ ==========
def kb_generate_confirm(subj: str, tid: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Сгенерировать", callback_data=f"generate_yes_{subj}_{tid}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"theme_{subj}_{tid}")]
    ])

# ========== ТАБЛИЦА МЕНДЕЛЕЕВА ==========
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

# ========== МЕНЮ ПРОФИЛЯ ==========
def kb_profile_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton(text="📅 Цель / Напоминание", callback_data="goal_reminder")],
        [InlineKeyboardButton(text="📌 Избранное", callback_data="my_favorites")],
        [InlineKeyboardButton(text="🔮 Прогноз баллов", callback_data="predict_score")],
        [InlineKeyboardButton(text="📉 Анализ слабых тем", callback_data="weak_analysis")],
        [InlineKeyboardButton(text="🌟 Мои подписки", callback_data="my_premiums")],
        [InlineKeyboardButton(text="🎁 Подарить подписку", callback_data="gift_menu")]
    ])
