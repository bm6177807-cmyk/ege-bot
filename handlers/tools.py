"""Образовательные инструменты для предметов ЕГЭ.

Доступные инструменты:
  math        — справочник формул (алгебра, геометрия, тригонометрия, …)
  physics     — физические константы + таблицы единиц
  geography   — тренажёр «Страна–столица»
  history     — карточки дат (история России / мировая история)
  informatics — перевод чисел между системами счисления (2 / 8 / 10 / 16)
  biology     — вычисление решётки Пеннета
  english     — SRS-тренажёр слов для ЕГЭ
"""

import random
import re
from collections import Counter, defaultdict
from itertools import product as iter_product

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from .states import Form
from data.tools.math_formulas import MATH_FORMULA_CATEGORIES
from data.tools.physics_constants import PHYSICS_CONSTANTS, PHYSICS_UNIT_TABLES
from data.tools.geo_capitals import GEO_CAPITALS
from data.tools.history_dates import HISTORY_DATES
from data.tools.english_words import ENGLISH_WORDS

router = Router()

# ─────────────────── вспомогательные данные ───────────────────

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
}

# Перечень инструментов каждого предмета: (callback_data, текст кнопки)
SUBJECT_TOOLS: dict[str, list[tuple[str, str]]] = {
    "math": [
        ("tool_math_formulas", "📐 Справочник формул"),
    ],
    "physics": [
        ("tool_phys_const", "🔬 Физические константы"),
        ("tool_phys_units", "📏 Таблицы единиц"),
    ],
    "geography": [
        ("tool_geo_quiz", "🌍 Тренажёр «Страна–столица»"),
    ],
    "history": [
        ("tool_hist_cards", "📅 Карточки дат"),
    ],
    "informatics": [
        ("tool_info_convert", "🔢 Перевод систем счисления"),
    ],
    "biology": [
        ("tool_bio_genetics", "🧬 Решётка Пеннета"),
    ],
    "english": [
        ("tool_eng_words", "📖 Слова для ЕГЭ (SRS)"),
    ],
}

# Все предметы, у которых есть инструменты
TOOL_SUBJECTS = set(SUBJECT_TOOLS.keys())


# ─────────────────── МЕНЮ ИНСТРУМЕНТОВ ПРЕДМЕТА ───────────────

@router.callback_query(F.data.in_(
    {"tool_math", "tool_physics", "tool_geography",
     "tool_history", "tool_informatics", "tool_biology", "tool_english"}
))
async def show_tools_menu(callback: CallbackQuery, state: FSMContext) -> None:
    subj = callback.data[len("tool_"):]
    name = _SUBJECT_NAMES.get(subj, subj)
    tools = SUBJECT_TOOLS.get(subj, [])

    await state.clear()

    buttons = [
        [InlineKeyboardButton(text=label, callback_data=cb)]
        for cb, label in tools
    ]
    buttons.append(
        [InlineKeyboardButton(text="← Назад к предмету", callback_data=f"subj_{subj}")]
    )

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        f"🧰 *Инструменты: {name}*\n\nВыбери инструмент:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════
#  МАТЕМАТИКА — СПРАВОЧНИК ФОРМУЛ
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "tool_math_formulas")
async def math_formulas_menu(callback: CallbackQuery, state: FSMContext) -> None:
    buttons = [
        [InlineKeyboardButton(text=data["name"], callback_data=f"tool_math_cat_{cat}")]
        for cat, data in MATH_FORMULA_CATEGORIES.items()
    ]
    buttons.append(
        [InlineKeyboardButton(text="← К инструментам", callback_data="tool_math")]
    )

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        "📐 *Справочник математических формул*\n\nВыбери раздел:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tool_math_cat_"))
async def math_formula_category(callback: CallbackQuery, state: FSMContext) -> None:
    cat = callback.data[len("tool_math_cat_"):]
    cat_data = MATH_FORMULA_CATEGORIES.get(cat)
    if not cat_data:
        await callback.answer("Раздел не найден")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← К разделам", callback_data="tool_math_formulas")],
        [InlineKeyboardButton(text="← К инструментам", callback_data="tool_math")],
    ])

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        f"{cat_data['name']}\n\n{cat_data['content']}",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════
#  ФИЗИКА — КОНСТАНТЫ И ЕДИНИЦЫ
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "tool_phys_const")
async def physics_constants(callback: CallbackQuery, state: FSMContext) -> None:
    lines = ["🔬 *Физические константы (ЕГЭ)*\n"]
    for name, symbol, value in PHYSICS_CONSTANTS:
        lines.append(f"• *{name}* ({symbol}) = {value}")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← К инструментам", callback_data="tool_physics")]
    ])

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        "\n".join(lines), reply_markup=kb, parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "tool_phys_units")
async def physics_units_menu(callback: CallbackQuery, state: FSMContext) -> None:
    buttons = [
        [InlineKeyboardButton(text=data["name"], callback_data=f"tool_phys_unit_{cat}")]
        for cat, data in PHYSICS_UNIT_TABLES.items()
    ]
    buttons.append(
        [InlineKeyboardButton(text="← К инструментам", callback_data="tool_physics")]
    )

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        "📏 *Таблицы единиц измерения*\n\nВыбери раздел:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tool_phys_unit_"))
async def physics_unit_table(callback: CallbackQuery, state: FSMContext) -> None:
    cat = callback.data[len("tool_phys_unit_"):]
    data = PHYSICS_UNIT_TABLES.get(cat)
    if not data:
        await callback.answer("Раздел не найден")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← К таблицам", callback_data="tool_phys_units")],
        [InlineKeyboardButton(text="← К инструментам", callback_data="tool_physics")],
    ])

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        f"{data['name']}\n\n{data['content']}",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════
#  ГЕОГРАФИЯ — ТРЕНАЖЁР «СТРАНА–СТОЛИЦА»
# ═══════════════════════════════════════════════════════════════

def _new_geo_question() -> dict:
    """Выбрать случайную страну и сгенерировать 4 варианта ответа."""
    idx = random.randrange(len(GEO_CAPITALS))
    country, correct = GEO_CAPITALS[idx]
    wrong_pool = [cap for _, cap in GEO_CAPITALS if cap != correct]
    wrong = random.sample(wrong_pool, min(3, len(wrong_pool)))
    options = wrong + [correct]
    random.shuffle(options)
    return {
        "country": country,
        "correct": correct,
        "options": options,
        "correct_idx": options.index(correct),
    }


def _kb_geo_question(options: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=opt, callback_data=f"tool_geo_ans_{i}")]
        for i, opt in enumerate(options)
    ]
    buttons.append(
        [InlineKeyboardButton(text="🏳️ Завершить тренажёр", callback_data="tool_geo_stop")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "tool_geo_quiz")
async def geo_quiz_start(callback: CallbackQuery, state: FSMContext) -> None:
    q = _new_geo_question()
    await state.update_data(
        geo_country=q["country"],
        geo_correct=q["correct"],
        geo_options=q["options"],
        geo_correct_idx=q["correct_idx"],
        geo_score=0,
        geo_total=0,
    )
    await state.set_state(Form.tool_geo_quiz)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        f"🌍 *Тренажёр «Страна–Столица»*\n\n"
        f"Вопрос: Какова столица *{q['country']}*?",
        reply_markup=_kb_geo_question(q["options"]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(Form.tool_geo_quiz, F.data.startswith("tool_geo_ans_"))
async def geo_quiz_answer(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        idx = int(callback.data.rsplit("_", 1)[-1])
    except (ValueError, IndexError):
        await callback.answer("⚠️ Ошибка обработки ответа. Попробуйте снова.")
        return
    data = await state.get_data()
    correct_idx: int = data.get("geo_correct_idx", -1)
    correct: str = data.get("geo_correct", "?")
    country: str = data.get("geo_country", "?")
    options: list = data.get("geo_options", [])
    score: int = data.get("geo_score", 0)
    total: int = data.get("geo_total", 0)

    total += 1
    if idx == correct_idx:
        score += 1
        result_text = f"✅ *Верно!* Столица {country} — {correct}."
    else:
        chosen = options[idx] if idx < len(options) else "?"
        result_text = (
            f"❌ *Неверно.* Ты ответил: {chosen}.\n"
            f"Правильный ответ: *{correct}* — столица {country}."
        )

    await state.update_data(geo_score=score, geo_total=total)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Следующий вопрос", callback_data="tool_geo_next")],
        [InlineKeyboardButton(text="🏳️ Завершить", callback_data="tool_geo_stop")],
    ])

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        f"{result_text}\n\n📊 Счёт: *{score}/{total}*",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(Form.tool_geo_quiz, F.data == "tool_geo_next")
async def geo_quiz_next(callback: CallbackQuery, state: FSMContext) -> None:
    q = _new_geo_question()
    await state.update_data(
        geo_country=q["country"],
        geo_correct=q["correct"],
        geo_options=q["options"],
        geo_correct_idx=q["correct_idx"],
    )

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        f"🌍 *Тренажёр «Страна–Столица»*\n\n"
        f"Вопрос: Какова столица *{q['country']}*?",
        reply_markup=_kb_geo_question(q["options"]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(Form.tool_geo_quiz, F.data == "tool_geo_stop")
async def geo_quiz_stop(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    score: int = data.get("geo_score", 0)
    total: int = data.get("geo_total", 0)
    await state.clear()

    pct = round(score * 100 / total) if total > 0 else 0
    if pct >= 80:
        verdict = "🏆 Отличный результат!"
    elif pct >= 50:
        verdict = "👍 Неплохо, продолжай тренироваться!"
    else:
        verdict = "💪 Нужно больше практики!"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Начать заново", callback_data="tool_geo_quiz")],
        [InlineKeyboardButton(text="← К инструментам", callback_data="tool_geography")],
    ])

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        f"🌍 *Тренажёр завершён!*\n\n"
        f"Твой результат: *{score}/{total}* ({pct}%)\n\n{verdict}",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════
#  ИСТОРИЯ — КАРТОЧКИ ДАТ
# ═══════════════════════════════════════════════════════════════

def _pick_hist_card(cat: str, exclude: list | None = None) -> tuple | None:
    """Выбрать случайную карточку, по возможности исключая уже показанные."""
    cards = HISTORY_DATES.get(cat, [])
    if not cards:
        return None
    pool = (
        [(i, cards[i][0], cards[i][1]) for i in range(len(cards)) if i not in exclude]
        if exclude and len(exclude) < len(cards)
        else [(i, cards[i][0], cards[i][1]) for i in range(len(cards))]
    )
    idx, date, event = random.choice(pool)
    return idx, date, event  # idx, дата, событие


@router.callback_query(F.data == "tool_hist_cards")
async def hist_cards_menu(callback: CallbackQuery, state: FSMContext) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 История России", callback_data="tool_hist_cat_russia")],
        [InlineKeyboardButton(text="🌍 Всемирная история", callback_data="tool_hist_cat_world")],
        [InlineKeyboardButton(text="← К инструментам", callback_data="tool_history")],
    ])

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        "📅 *Карточки дат*\n\nВыбери раздел:",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tool_hist_cat_"))
async def hist_cards_start(callback: CallbackQuery, state: FSMContext) -> None:
    cat = callback.data[len("tool_hist_cat_"):]
    result = _pick_hist_card(cat)
    if not result:
        await callback.answer("Нет данных для этого раздела")
        return

    idx, date, event = result
    await state.update_data(hist_cat=cat, hist_idx=idx, hist_shown=[idx])
    await state.set_state(Form.tool_hist_cards)

    cat_name = "История России" if cat == "russia" else "Всемирная история"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Показать дату", callback_data="tool_hist_reveal")],
        [InlineKeyboardButton(text="➡️ Следующая карточка", callback_data="tool_hist_skip")],
        [InlineKeyboardButton(text="🏳️ Завершить", callback_data="tool_hist_stop")],
    ])

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        f"📅 *{cat_name}*\n\n*Событие:*\n{event}\n\nКогда это произошло?",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(Form.tool_hist_cards, F.data == "tool_hist_reveal")
async def hist_reveal(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    cat: str = data.get("hist_cat", "russia")
    idx: int = data.get("hist_idx", 0)
    cards = HISTORY_DATES.get(cat, [])
    if idx >= len(cards):
        await callback.answer("Ошибка: карточка не найдена")
        return

    date, event = cards[idx]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Следующая карточка", callback_data="tool_hist_next")],
        [InlineKeyboardButton(text="🏳️ Завершить", callback_data="tool_hist_stop")],
    ])

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        f"📅 *{date}*\n\n{event}",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(
    Form.tool_hist_cards,
    F.data.in_({"tool_hist_next", "tool_hist_skip"}),
)
async def hist_next_card(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    cat: str = data.get("hist_cat", "russia")
    shown: list = data.get("hist_shown", [])

    result = _pick_hist_card(cat, exclude=shown)
    if not result:
        # Все карточки уже показаны — сбрасываем историю
        result = _pick_hist_card(cat)
        shown = []

    idx, date, event = result
    shown = (shown + [idx])[-30:]  # хранить не более 30 последних
    await state.update_data(hist_idx=idx, hist_shown=shown)

    cat_name = "История России" if cat == "russia" else "Всемирная история"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Показать дату", callback_data="tool_hist_reveal")],
        [InlineKeyboardButton(text="➡️ Следующая карточка", callback_data="tool_hist_skip")],
        [InlineKeyboardButton(text="🏳️ Завершить", callback_data="tool_hist_stop")],
    ])

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        f"📅 *{cat_name}*\n\n*Событие:*\n{event}\n\nКогда это произошло?",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(Form.tool_hist_cards, F.data == "tool_hist_stop")
async def hist_stop(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Начать заново", callback_data="tool_hist_cards")],
        [InlineKeyboardButton(text="← К инструментам", callback_data="tool_history")],
    ])

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        "📅 *Тренажёр завершён!*\n\n"
        "Продолжай повторять даты — это важный раздел ЕГЭ по истории!",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════
#  ИНФОРМАТИКА — ПЕРЕВОД СИСТЕМ СЧИСЛЕНИЯ
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "tool_info_convert")
async def info_convert_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Form.tool_info_input)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        "🔢 *Перевод систем счисления*\n\n"
        "Введи число и основание его системы счисления через пробел:\n"
        "`<число> <основание>`\n\n"
        "*Примеры:*\n"
        "• `1010 2` — двоичное 1010\n"
        "• `255 10` — десятичное 255\n"
        "• `FF 16` — шестнадцатеричное FF\n"
        "• `377 8` — восьмеричное 377\n\n"
        "_Поддерживаемые основания: 2, 8, 10, 16_\n"
        "_Для отмены отправь /start_",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(Form.tool_info_input)
async def info_convert_process(message: Message, state: FSMContext) -> None:
    text = message.text.strip() if message.text else ""
    parts = text.split()

    if len(parts) != 2:
        await message.answer(
            "⚠️ Неверный формат. Введи число и основание через пробел.\n"
            "Пример: `1010 2` или `255 10`",
            parse_mode="Markdown",
        )
        return

    num_str, base_str = parts
    try:
        base = int(base_str)
        if base not in (2, 8, 10, 16):
            await message.answer(
                "⚠️ Поддерживаемые основания: *2, 8, 10, 16*.",
                parse_mode="Markdown",
            )
            return
        value = int(num_str, base)
    except ValueError:
        await message.answer(
            f"⚠️ Число `{num_str}` некорректно для системы с основанием *{base_str}*.",
            parse_mode="Markdown",
        )
        return

    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Перевести ещё", callback_data="tool_info_convert")],
        [InlineKeyboardButton(text="← К инструментам", callback_data="tool_informatics")],
    ])

    await message.answer(
        f"🔢 *Результат перевода*\n\n"
        f"Исходное число: `{num_str.upper()}` (основание {base})\n\n"
        f"• Двоичная      (2):  `{bin(value)[2:]}`\n"
        f"• Восьмеричная  (8):  `{oct(value)[2:]}`\n"
        f"• Десятичная   (10):  `{value}`\n"
        f"• Шестнадцатеричная (16):  `{hex(value)[2:].upper()}`",
        reply_markup=kb,
        parse_mode="Markdown",
    )


# ═══════════════════════════════════════════════════════════════
#  БИОЛОГИЯ — РЕШЁТКА ПЕННЕТА
# ═══════════════════════════════════════════════════════════════

def _parse_gametes(genotype: str) -> list:
    """Получить список гамет из диплоидного генотипа.

    Паттерн ищет пары аллелей:
      - [A-Z][a-z]  — гетерозиготный локус (Aa)
      - [A-Z]{2}    — гомозиготный доминантный (AA)
      - [a-z]{2}    — гомозиготный рецессивный (aa)
    """
    pairs = re.findall(r"[A-Z][a-z]|[A-Z]{2}|[a-z]{2}", genotype.strip())
    if not pairs:
        return []
    loci_gametes = []
    for pair in pairs:
        if pair[0] == pair[1]:  # гомозиготный локус: AA или aa
            loci_gametes.append([pair[0]])
        else:                    # гетерозиготный локус: Aa
            loci_gametes.append([pair[0], pair[1]])
    return ["".join(combo) for combo in iter_product(*loci_gametes)]


def _sort_genotype(alleles: str) -> str:
    """Нормализовать генотип: для каждого локуса — заглавная буква перед строчной."""
    loci: dict = defaultdict(list)
    for c in alleles:
        loci[c.lower()].append(c)
    result = []
    for letter in sorted(loci.keys()):
        result.extend(sorted(loci[letter], key=lambda x: x.islower()))
    return "".join(result)


def _compute_punnett(p1: str, p2: str) -> dict | None:
    g1 = _parse_gametes(p1)
    g2 = _parse_gametes(p2)
    if not g1 or not g2:
        return None

    offspring = [_sort_genotype(a + b) for a in g1 for b in g2]
    counts = Counter(offspring)
    total = len(offspring)

    return {
        "p1": p1, "p2": p2,
        "g1": g1, "g2": g2,
        "counts": counts, "total": total,
    }


def _phenotype_class(geno: str) -> tuple:
    """Вернуть фенотипический класс как кортеж (True=доминантный, False=рецессивный по каждому локусу)."""
    loci: dict = defaultdict(list)
    for c in geno:
        loci[c.lower()].append(c)
    return tuple(any(c.isupper() for c in alleles) for _, alleles in sorted(loci.items()))


def _format_punnett(res: dict) -> str:
    g1, g2 = res["g1"], res["g2"]
    lines = [f"🧬 *Решётка Пеннета: {res['p1']} × {res['p2']}*\n"]

    lines.append(f"*Гаметы ♀:* {', '.join(g1)}")
    lines.append(f"*Гаметы ♂:* {', '.join(g2)}\n")

    # Для моногибридного скрещивания рисуем таблицу 2×2
    if len(g1) <= 2 and len(g2) <= 2:
        header = "     " + "    ".join(g2)
        sep = "─" * (len(header) + 2)
        lines.append(f"`{header}`")
        lines.append(f"`{sep}`")
        for ga in g1:
            cells = [_sort_genotype(ga + gb) for gb in g2]
            lines.append(f"`{ga}  │ {'  │  '.join(cells)}  │`")
        lines.append("")

    lines.append("*Генотипы:*")
    for geno, cnt in sorted(res["counts"].items()):
        pct = round(cnt * 100 / res["total"])
        lines.append(f"  `{geno}` — {cnt}/{res['total']} ({pct}%)")

    # Фенотипические классы
    pheno_counts: Counter = Counter()
    for geno, cnt in res["counts"].items():
        pheno_counts[_phenotype_class(geno)] += cnt

    total = res["total"]
    num_loci = len(_phenotype_class(next(iter(res["counts"]), ""))) if res["counts"] else 0

    lines.append("\n*Фенотипы* (полное доминирование):")
    if num_loci == 1:
        dom = pheno_counts.get((True,), 0)
        rec = pheno_counts.get((False,), 0)
        lines.append(f"  Доминантный: {dom}/{total} ({dom * 100 // total}%)")
        if rec > 0:
            lines.append(f"  Рецессивный: {rec}/{total} ({rec * 100 // total}%)")
    else:
        # Для нескольких локусов — показать все фенотипические классы
        locus_letters = sorted(set(c.lower() for c in (res["p1"] + res["p2"]) if c.isalpha()))
        for pheno_key, cnt in sorted(pheno_counts.items(), reverse=True):
            desc_parts = []
            for i, is_dom in enumerate(pheno_key):
                letter = locus_letters[i].upper() if i < len(locus_letters) else "?"
                desc_parts.append(f"{letter}_" if is_dom else f"{letter.lower()}{letter.lower()}")
            desc = " ".join(desc_parts)
            pct = round(cnt * 100 / total)
            lines.append(f"  {desc}: {cnt}/{total} ({pct}%)")

    return "\n".join(lines)


@router.callback_query(F.data == "tool_bio_genetics")
async def bio_genetics_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Form.tool_bio_input)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        "🧬 *Решётка Пеннета*\n\n"
        "Введи генотипы родителей через × (или латинскую x):\n"
        "`<генотип1> × <генотип2>`\n\n"
        "*Примеры:*\n"
        "• `Aa × Aa` — моногибридное скрещивание\n"
        "• `AA × aa` — скрещивание гомозигот\n"
        "• `Aa × aa` — анализирующее скрещивание\n"
        "• `AaBb × AaBb` — дигибридное скрещивание\n\n"
        "_Доминантный аллель — заглавная буква (A), рецессивный — строчная (a)._\n"
        "_Для отмены отправь /start_",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(Form.tool_bio_input)
async def bio_genetics_process(message: Message, state: FSMContext) -> None:
    text = message.text.strip() if message.text else ""
    parts = re.split(r"\s*[×xX]\s*", text)

    if len(parts) != 2:
        await message.answer(
            "⚠️ Неверный формат. Введи два генотипа через ×.\n"
            "Пример: `Aa × Aa`",
            parse_mode="Markdown",
        )
        return

    p1, p2 = parts[0].strip(), parts[1].strip()
    result = _compute_punnett(p1, p2)

    if result is None:
        await message.answer(
            "⚠️ Не удалось разобрать генотипы.\n"
            "Убедись, что используешь стандартную запись:\n"
            "заглавная буква — доминантный аллель (A),\n"
            "строчная буква — рецессивный аллель (a).\n"
            "Пример: `Aa × Aa`",
            parse_mode="Markdown",
        )
        return

    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Решить другую задачу", callback_data="tool_bio_genetics")],
        [InlineKeyboardButton(text="← К инструментам", callback_data="tool_biology")],
    ])

    await message.answer(
        _format_punnett(result), reply_markup=kb, parse_mode="Markdown"
    )


# ═══════════════════════════════════════════════════════════════
#  АНГЛИЙСКИЙ — SRS СЛОВА
# ═══════════════════════════════════════════════════════════════

@router.callback_query(F.data == "tool_eng_words")
async def eng_words_menu(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "📖 *Слова для ЕГЭ — тренажёр*\n\n"
        f"В базе {len(ENGLISH_WORDS)} слов.\n"
        "Нажми «Следующее слово», чтобы начать:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Следующее слово", callback_data="tool_eng_next")],
            [InlineKeyboardButton(text="← Назад", callback_data="tool_english")],
        ]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "tool_eng_next")
async def eng_word_next(callback: CallbackQuery, state: FSMContext) -> None:
    word, translation, hint = random.choice(ENGLISH_WORDS)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        f"📖 *{word}*\n\n"
        f"🇷🇺 {translation}\n"
        f"💡 _{hint}_",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Следующее слово", callback_data="tool_eng_next")],
            [InlineKeyboardButton(text="← К списку инструментов", callback_data="tool_english")],
        ]),
        parse_mode="Markdown",
    )
    await callback.answer()
