# handlers/profile.py
import re
import os
import uuid
import urllib.parse
import logging
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice, PreCheckoutQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext

import database as db
from data import TASKS
from keyboards import kb_profile_menu, kb_cancel, kb_main
from payments import STARS_PRICES, YOOMONEY_PRICES, build_stars_payload, parse_stars_payload
from .states import Form

router = Router()
logger = logging.getLogger(__name__)

ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i]
BOT_USERNAME = os.getenv("BOT_USERNAME", "")
YOOMONEY_RECEIVER = os.getenv("YOOMONEY_RECEIVER", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")

SUBJECT_NAMES = {
    "chemistry": "Химия 🧪",
    "biology": "Биология 🌿",
    "math": "Математика 📐",
    "physics": "Физика ⚡",
    "informatics": "Информатика 💻",
    "history": "История 📜",
    "geography": "География 🌍",
    "social": "Обществознание 🏛️",
    "literature": "Литература 📖",
    "russian": "Русский язык 🇷🇺",
}


def subject_name(key: str) -> str:
    return SUBJECT_NAMES.get(key, key.capitalize())


def _build_yoomoney_url(order_id: str, subject: str, days: int) -> str:
    """Build a YooMoney Quickpay payment URL with proper URL-encoding."""
    amount = YOOMONEY_PRICES[days]
    success_url = PUBLIC_BASE_URL or (f"https://t.me/{BOT_USERNAME}" if BOT_USERNAME else "")
    params = {
        "receiver": YOOMONEY_RECEIVER,
        "quickpay-form": "shop",
        "targets": f"Премиум {subject_name(subject)} {days} дней",
        "sum": str(amount),
        "paymentType": "AC",
        "label": order_id,
    }
    if success_url:
        params["successURL"] = success_url
    return "https://yoomoney.ru/quickpay/confirm?" + urllib.parse.urlencode(params)


async def _give_referral_bonus(bot: Bot, user_id: int):
    """Give +3 days on all subjects to referrer after first purchase by referred user."""
    ref = db.get_referrer_for_user(user_id)
    if ref and ref["premium_bonus_given"] == 0:
        referrer_id = ref["referrer_id"]
        for subj in TASKS.keys():
            db.set_subject_premium(referrer_id, subj, 3)
        db.mark_referral_bonus_given(user_id)
        try:
            await bot.send_message(
                referrer_id,
                "🎉 Твой друг совершил первую покупку!\n"
                "Тебе начислен бонус: +3 дня на все предметы.",
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить реферера {referrer_id}: {e}")

# ========== МЕНЮ ПРОФИЛЯ ==========
@router.message(F.text == "📊 Профиль")
async def profile_menu(message: Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")],
        [InlineKeyboardButton(text="📅 Цель / Напоминание", callback_data="goal_reminder")],
        [InlineKeyboardButton(text="📌 Избранное", callback_data="my_favorites")],
        [InlineKeyboardButton(text="🔮 Прогноз баллов", callback_data="predict_score")],
        [InlineKeyboardButton(text="📉 Анализ слабых тем", callback_data="weak_analysis")],
        [InlineKeyboardButton(text="🌟 Мои подписки", callback_data="my_premiums")],
        [InlineKeyboardButton(text="🎁 Подарить подписку", callback_data="gift_menu")],
        [InlineKeyboardButton(text="📨 Пригласить друга", callback_data="referral_link")],
        [InlineKeyboardButton(text="🔔 Настройка новостей", callback_data="news_settings")],
    ])
    await message.answer("Твой профиль:", reply_markup=kb)

# ========== МОИ ПОДПИСКИ ==========
@router.callback_query(F.data == "my_premiums")
async def my_premiums(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    premiums = db.get_user_premiums(user_id)
    if not premiums:
        text = "У тебя нет активных подписок на предметы."
    else:
        lines = ["**Твои активные подписки:**"]
        for p in premiums:
            lines.append(f"• {p['subject']} – до {p['expires_at']}")
        text = "\n".join(lines)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в профиль", callback_data="back_to_profile")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


# ========== РЕФЕРАЛЬНАЯ ПРОГРАММА ==========
@router.callback_query(F.data == "referral_link")
async def referral_link(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    count = db.get_referral_count(user_id)
    bonuses = db.get_referral_bonus(user_id)
    if BOT_USERNAME:
        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        link_text = f"`{link}`"
    else:
        link_text = "_(ссылка недоступна: BOT\\_USERNAME не задан в настройках)_"
    text = (
        "📨 **Пригласить друга**\n\n"
        f"Твоя реферальная ссылка:\n{link_text}\n\n"
        "Как это работает:\n"
        "• Друг, перешедший по ссылке, получает **+1 день** на все предметы.\n"
        "• Ты получаешь **+3 дня** на все предметы после первой покупки друга.\n\n"
        f"👥 Приглашено друзей: **{count}**\n"
        f"🎁 Бонусов получено: **{bonuses}**"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в профиль", callback_data="back_to_profile")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


# ========== МЕНЮ ПОДАРКА ==========
@router.callback_query(F.data == "gift_menu")
async def gift_menu(callback: CallbackQuery, state: FSMContext):
    buttons = [
        [InlineKeyboardButton(text=subject_name(k), callback_data=f"gift_subject_{k}")]
        for k in TASKS.keys()
    ]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile")])
    await callback.message.edit_text(
        "Выбери предмет, подписку на который хочешь подарить:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("gift_subject_"))
async def gift_subject(callback: CallbackQuery, state: FSMContext):
    subject = callback.data[len("gift_subject_"):]
    await state.update_data(gift_subject=subject)
    await callback.message.edit_text(
        f"Введи Telegram ID пользователя, которому хочешь подарить подписку на {subject}.\n\n"
        "Он может узнать свой ID у бота @userinfobot."
    )
    await state.set_state(Form.gift_user_input)
    await callback.answer()

@router.message(Form.gift_user_input)
async def gift_user_input(message: Message, state: FSMContext):
    try:
        target_id = int(message.text.strip())
    except Exception:
        await message.answer("❌ Неверный формат ID. Попробуй ещё раз или отправь /cancel.")
        return
    data = await state.get_data()
    subject = data.get("gift_subject")
    await state.update_data(gift_target=target_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="7 дней - 100 ⭐", callback_data=f"gift_pay_{subject}_{target_id}_7")],
        [InlineKeyboardButton(text="30 дней - 300 ⭐", callback_data=f"gift_pay_{subject}_{target_id}_30")],
        [InlineKeyboardButton(text="90 дней - 750 ⭐", callback_data=f"gift_pay_{subject}_{target_id}_90")],
        [InlineKeyboardButton(text="← Отмена", callback_data="back_to_profile")]
    ])
    await message.answer(f"Выбери срок подписки для пользователя {target_id} по предмету {subject}:", reply_markup=kb)
    await state.clear()

@router.callback_query(F.data.startswith("gift_pay_"))
async def gift_pay(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    subject = parts[2]
    target_id = int(parts[3])
    days = int(parts[4])
    expires = db.gift_subject_premium(callback.from_user.id, target_id, subject, days)
    await callback.message.edit_text(
        f"✅ Подарок отправлен!\n"
        f"Пользователь {target_id} получил {days} дней премиума по предмету {subject} (до {expires})."
    )
    await callback.answer()

# ========== СТАТИСТИКА ==========
@router.callback_query(F.data == "my_stats")
async def cb_my_stats(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user = db.get_user(callback.from_user.id)
    percent = (user['correct_answers'] / user['total_answers'] * 100) if user['total_answers'] > 0 else 0
    await callback.message.answer(
        f"📊 **Твоя статистика:**\n"
        f"Уровень: {user['level']}\n"
        f"Опыт: {user['exp']}\n"
        f"Всего ответов: {user['total_answers']}\n"
        f"Правильных: {user['correct_answers']}\n"
        f"Процент: {percent:.1f}%\n"
        f"Дата экзамена: {user.get('exam_date', 'не указана')}",
        parse_mode="Markdown"
    )
    await callback.answer()

# ========== ИЗБРАННОЕ ==========
@router.callback_query(F.data == "my_favorites")
async def cb_my_favorites(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user_id = callback.from_user.id
    favs = db.get_favorites(user_id)
    if not favs:
        await callback.message.answer("📭 У тебя пока нет избранных конспектов. Сохраняй их звездочкой в меню темы.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for fav in favs:
        subject = fav['subject']
        theme_id = fav['theme_id']
        theme_name = TASKS.get(subject, {}).get(theme_id, {}).get("name", theme_id)
        if len(theme_name) > 40:
            theme_name = theme_name[:40] + "…"
        kb.inline_keyboard.append([InlineKeyboardButton(text=theme_name, callback_data=f"cons_{subject}_{theme_id}")])
    await callback.message.answer("📌 **Твои избранные конспекты:**", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

# ========== ЦЕЛЬ И НАПОМИНАНИЯ ==========
@router.callback_query(F.data == "goal_reminder")
async def cb_goal_reminder(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    count, goal = db.get_daily_goal(callback.from_user.id)
    text = f"📅 Ежедневная цель: {count}/{goal} заданий.\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить цель", callback_data="set_goal")],
        [InlineKeyboardButton(text="Установить напоминание", callback_data="set_reminder")]
    ])
    await callback.message.answer(text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "set_goal")
async def set_goal_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введи новую ежедневную цель (число заданий в день):")
    await state.set_state(Form.reminder_set)
    await callback.answer()

@router.message(Form.reminder_set)
async def process_new_goal(message: Message, state: FSMContext):
    try:
        goal = int(message.text.strip())
        if goal < 1 or goal > 50:
            raise ValueError
        db.set_daily_goal(message.from_user.id, goal)
        await message.answer(f"✅ Ежедневная цель изменена на {goal} заданий.", reply_markup=kb_main())
        await state.clear()
    except:
        await message.answer("❌ Некорректное число. Введи число от 1 до 50.", reply_markup=kb_cancel())

@router.callback_query(F.data == "set_reminder")
async def set_reminder_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введи время для напоминания в формате HH:MM (например, 19:00):")
    await state.set_state(Form.reminder_set)
    await callback.answer()

@router.message(Form.reminder_set)
async def process_reminder_time(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Установка отменена.", reply_markup=kb_main())
        await state.clear()
        return
    time_str = message.text.strip()
    if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time_str):
        await message.answer("Неверный формат. Используй HH:MM, например 09:30 или 19:00", reply_markup=kb_cancel())
        return
    db.set_reminder(message.from_user.id, time_str)
    await message.answer(f"✅ Напоминание установлено на {time_str} каждый день.", reply_markup=kb_main())
    await state.clear()

# ========== ПРОГНОЗ БАЛЛОВ И АНАЛИЗ ==========
@router.callback_query(F.data == "predict_score")
async def cb_predict_score(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(
        "🔮 **Прогноз баллов ЕГЭ**\n\n"
        "После прохождения варианта ты получишь прогноз на основе твоих результатов.\n"
        "Пока нет данных. Пройди вариант в разделе «Тренировка»."
    )
    await callback.answer()

@router.callback_query(F.data == "weak_analysis")
async def cb_weak_analysis(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    stats = db.get_theme_stats(user_id)
    weak_themes = []
    for s in stats:
        if s['total'] >= 3 and (s['correct'] / s['total']) < 0.6:
            theme_name = TASKS.get(s['subject'], {}).get(s['theme_id'], {}).get("name", s['theme_id'])
            percent = (s['correct'] / s['total']) * 100
            weak_themes.append(f"• {theme_name} – {percent:.0f}% правильных")

    if weak_themes:
        text = "📉 **Темы, требующие внимания:**\n" + "\n".join(weak_themes)
    else:
        text = "✅ У тебя нет слабых тем! Так держать!"

    await callback.message.delete()
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

# ========== КУПЛЯ ПРЕМИУМА (ОБЩИЙ РАЗДЕЛ) ==========
@router.message(F.text == "⭐ Купить премиум")
async def show_premium_menu_message(message: Message, state: FSMContext):
    await _send_premium_subject_menu(message)


@router.callback_query(F.data == "premium")
async def show_premium_menu_callback(callback: CallbackQuery, state: FSMContext):
    await _send_premium_subject_menu(callback.message)
    await callback.answer()


async def _send_premium_subject_menu(target: Message):
    buttons = [
        [InlineKeyboardButton(text=subject_name(k), callback_data=f"buy_subject_premium_{k}")]
        for k in TASKS.keys()
    ]
    buttons.append([InlineKeyboardButton(text="← Назад в профиль", callback_data="back_to_profile")])
    await target.answer(
        "🌟 **Премиум-доступ** 🌟\n\nВыбери предмет, на который хочешь оформить подписку:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("buy_subject_premium_"))
async def buy_subject_premium(callback: CallbackQuery, state: FSMContext):
    subject = callback.data[len("buy_subject_premium_"):]
    name = subject_name(subject)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"1 месяц  — ⭐ {STARS_PRICES[30]} / 💳 {YOOMONEY_PRICES[30]} ₽",
            callback_data=f"pay_subject_{subject}_30"
        )],
        [InlineKeyboardButton(
            text=f"3 месяца — ⭐ {STARS_PRICES[90]} / 💳 {YOOMONEY_PRICES[90]} ₽",
            callback_data=f"pay_subject_{subject}_90"
        )],
        [InlineKeyboardButton(
            text=f"6 месяцев — ⭐ {STARS_PRICES[180]} / 💳 {YOOMONEY_PRICES[180]} ₽",
            callback_data=f"pay_subject_{subject}_180"
        )],
        [InlineKeyboardButton(text="← Назад", callback_data="premium")],
    ])
    await callback.message.edit_text(
        f"🌟 **{name}** — выбери срок подписки:",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_subject_"))
async def pay_subject_method(callback: CallbackQuery, state: FSMContext):
    """Show payment method selection (Stars vs YooMoney)."""
    remainder = callback.data[len("pay_subject_"):]
    subject, days_str = remainder.rsplit("_", 1)
    days = int(days_str)
    name = subject_name(subject)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"⭐ Telegram Stars — {STARS_PRICES[days]} ⭐",
            callback_data=f"pay_stars_{subject}_{days}"
        )],
        [InlineKeyboardButton(
            text=f"💳 YooMoney — {YOOMONEY_PRICES[days]} ₽",
            callback_data=f"pay_yoomoney_{subject}_{days}"
        )],
        [InlineKeyboardButton(text="← Назад", callback_data=f"buy_subject_premium_{subject}")],
    ])
    await callback.message.edit_text(
        f"💰 **Оплата: {name}, {days} дней**\n\nВыбери способ оплаты:",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


# ===== TELEGRAM STARS =====
@router.callback_query(F.data.startswith("pay_stars_"))
async def pay_stars(callback: CallbackQuery, state: FSMContext, bot: Bot):
    remainder = callback.data[len("pay_stars_"):]
    subject, days_str = remainder.rsplit("_", 1)
    days = int(days_str)
    name = subject_name(subject)
    stars = STARS_PRICES[days]
    order_id = str(uuid.uuid4())
    payload = build_stars_payload(subject, days, order_id)

    logger.info(
        "Stars: pay_stars clicked user_id=%s subject=%s days=%s stars=%s order_id=%s",
        callback.from_user.id, subject, days, stars, order_id,
    )

    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"Премиум: {name} ({days} дней)",
            description=f"Доступ к задачам и конспектам по предмету «{name}» на {days} дней.",
            payload=payload,
            provider_token="",  # empty string required for Telegram Stars (XTR)
            currency="XTR",
            prices=[LabeledPrice(label=f"{days} дней", amount=stars)],
        )
        logger.info(
            "Stars: invoice sent user_id=%s subject=%s days=%s stars=%s order_id=%s",
            callback.from_user.id, subject, days, stars, order_id,
        )
    except Exception:
        logger.exception(
            "Stars: send_invoice failed user_id=%s subject=%s days=%s stars=%s",
            callback.from_user.id, subject, days, stars,
        )
        await callback.message.answer(
            "❌ Не удалось выставить счёт Telegram Stars.\n"
            "Попробуй позже или выбери оплату YooMoney."
        )

    await callback.answer()


@router.pre_checkout_query()
async def handle_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    logger.info(
        "Stars: pre_checkout_query from=%s payload=%s",
        pre_checkout_query.from_user.id,
        pre_checkout_query.invoice_payload,
    )
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def handle_successful_payment(message: Message, bot: Bot):
    sp = message.successful_payment
    logger.info(
        "Stars: successful_payment from=%s payload=%s telegram_charge_id=%s",
        message.from_user.id,
        sp.invoice_payload,
        sp.telegram_payment_charge_id,
    )

    # ── Parse payload ─────────────────────────────────────────────────────
    parsed = parse_stars_payload(sp.invoice_payload)
    if parsed is None:
        # Fallback: try legacy format "subject:days"
        try:
            subject, days_str = sp.invoice_payload.split(":", 1)
            order_id = str(uuid.uuid4())
            days = int(days_str)
            parsed = (order_id, subject, days)
        except Exception:
            logger.error("Stars: bad payment payload: %s", sp.invoice_payload)
            await message.answer(
                "✅ Оплата получена, но произошла ошибка активации. Свяжитесь с поддержкой."
            )
            return

    order_id, subject, days = parsed

    # ── Idempotency: skip if already processed ────────────────────────────
    if db.is_stars_payment_exists(sp.telegram_payment_charge_id):
        logger.warning(
            "Stars: duplicate payment ignored telegram_charge_id=%s",
            sp.telegram_payment_charge_id,
        )
        return

    # ── Persist payment record ────────────────────────────────────────────
    inserted = db.save_stars_payment(
        order_id=order_id,
        user_id=message.from_user.id,
        subject=subject,
        days=days,
        telegram_charge_id=sp.telegram_payment_charge_id,
        provider_charge_id=getattr(sp, "provider_payment_charge_id", None) or "",
    )
    if not inserted:
        # Race condition: another update snuck in
        logger.warning(
            "Stars: duplicate payment (race) telegram_charge_id=%s",
            sp.telegram_payment_charge_id,
        )
        return

    # ── Grant premium ─────────────────────────────────────────────────────
    expires = db.set_subject_premium(message.from_user.id, subject, days)
    name = subject_name(subject)
    await message.answer(
        f"✅ Оплата через Telegram Stars прошла успешно!\n"
        f"Премиум на **{name}** активирован на {days} дней (до {expires}).",
        parse_mode="Markdown",
    )
    await _give_referral_bonus(bot, message.from_user.id)


# ===== YOOMONEY =====
@router.callback_query(F.data.startswith("pay_yoomoney_"))
async def pay_yoomoney(callback: CallbackQuery, state: FSMContext):
    remainder = callback.data[len("pay_yoomoney_"):]
    subject, days_str = remainder.rsplit("_", 1)
    days = int(days_str)
    name = subject_name(subject)
    amount = YOOMONEY_PRICES[days]
    order_id = str(uuid.uuid4())
    db.save_pending_payment(order_id, callback.from_user.id, subject, days)
    pay_url = _build_yoomoney_url(order_id, subject, days)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 Оплатить {amount} ₽", url=pay_url)],
        [InlineKeyboardButton(text="← Назад", callback_data=f"pay_subject_{subject}_{days}")],
    ])
    await callback.message.edit_text(
        f"💳 **Оплата через YooMoney**\n\n"
        f"Предмет: **{name}**\n"
        f"Срок: **{days} дней**\n"
        f"Сумма: **{amount} ₽**\n\n"
        "Нажми кнопку, оплати и вернись — подписка активируется автоматически после подтверждения оплаты.",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


# ========== ОБРАБОТЧИК ВОЗВРАТА ==========
@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await profile_menu(callback.message, state)
    await callback.answer()

# ========== НАСТРОЙКА НОВОСТЕЙ ==========
def _news_text_and_kb(opt_in: bool):
    """Возвращает текст и клавиатуру для экрана настройки новостей."""
    status = "🔔 Вкл" if opt_in else "🔕 Выкл"
    toggle_label = "🔕 Отключить новости" if opt_in else "🔔 Включить новости"
    text = (
        "📢 Настройка уведомлений о новостях\n\n"
        f"Текущий статус: {status}\n\n"
        "Если новости включены, ты будешь получать объявления об обновлениях и новых функциях бота."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_label, callback_data="news_toggle")],
        [InlineKeyboardButton(text="🔙 Назад в профиль", callback_data="back_to_profile")],
    ])
    return text, kb


@router.callback_query(F.data == "news_settings")
async def news_settings(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    opt_in = db.get_news_opt_in(user_id)
    text, kb = _news_text_and_kb(opt_in)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "news_toggle")
async def news_toggle(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    new_val = not db.get_news_opt_in(user_id)
    db.set_news_opt_in(user_id, new_val)
    confirm = "✅ Новости включены." if new_val else "✅ Новости отключены."
    text, kb = _news_text_and_kb(new_val)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer(confirm)
