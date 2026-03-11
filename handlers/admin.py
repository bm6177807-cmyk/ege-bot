# handlers/admin.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import asyncio
import logging
import os
import sqlite3
import time

import database as db
from .states import Form
from keyboards import kb_cancel, kb_main

logger = logging.getLogger(__name__)

router = Router()
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

# Поддержка единственного ADMIN_TG_USER_ID (приоритет над ADMIN_IDS)
_single_admin = os.getenv("ADMIN_TG_USER_ID", "").strip()
if _single_admin:
    try:
        _single_admin_id = int(_single_admin)
        if _single_admin_id not in ADMIN_IDS:
            ADMIN_IDS.append(_single_admin_id)
    except ValueError:
        logger.warning("ADMIN_TG_USER_ID задан некорректно — рассылка отключена.")

if not ADMIN_IDS:
    logger.warning("Ни ADMIN_IDS, ни ADMIN_TG_USER_ID не заданы — команды рассылки отключены.")

# Лимит Telegram: не более 30 сообщений/сек в разные чаты (с запасом берём 20)
_BROADCAST_RATE = 20  # сообщений в секунду

@router.message(Command("givepremium"))
async def cmd_give_premium(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет прав на выполнение этой команды.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "❌ Использование: /givepremium <user_id> [дней]\n"
            "Пример: /givepremium 123456789 30"
        )
        return

    try:
        target_id = int(args[1])
        days = 30
        if len(args) >= 3:
            days = int(args[2])
            if days <= 0:
                raise ValueError
    except ValueError:
        await message.answer("❌ Неверный формат. Укажите корректный user_id и количество дней (целое положительное число).")
        return

    user_data = db.get_user(target_id)
    expires = (datetime.now() + timedelta(days=days)).date()
    # В старой системе был глобальный премиум; теперь будем выдавать на все предметы?
    # Для упрощения выдадим на все предметы (можно позже изменить)
    subjects = ["chemistry", "biology", "math", "physics", "informatics", "history", "geography", "social", "literature", "russian"]
    for subject in subjects:
        db.set_subject_premium(target_id, subject, days)
    
    await message.answer(
        f"✅ Премиум на все предметы выдан пользователю {target_id} на {days} дн. (до {expires.strftime('%d.%m.%Y')})"
    )

    try:
        await message.bot.send_message(
            target_id,
            f"🎉 Вам выдан премиум-доступ на все предметы на {days} дн. (до {expires.strftime('%d.%m.%Y')})\n"
            "Спасибо за использование бота!"
        )
    except:
        pass

@router.message(Command("removepremium"))
async def cmd_remove_premium(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет прав на выполнение этой команды.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /removepremium <user_id>")
        return

    try:
        target_id = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный формат user_id.")
        return

    # Удаляем записи из subject_premium
    conn = sqlite3.connect(db.DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM subject_premium WHERE user_id = ?", (target_id,))
    conn.commit()
    conn.close()

    await message.answer(f"✅ Премиум отключён у пользователя {target_id} (все предметы).")

    try:
        await message.bot.send_message(
            target_id,
            "🔕 Ваш премиум-доступ был отключён администратором."
        )
    except:
        pass

@router.message(Command("checkpremium"))
async def cmd_check_premium(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет прав на выполнение этой команды.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /checkpremium <user_id>")
        return

    try:
        target_id = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный формат user_id.")
        return

    premiums = db.get_user_premiums(target_id)
    if premiums:
        lines = [f"Активные подписки пользователя {target_id}:"]
        for p in premiums:
            lines.append(f"• {p['subject']} – до {p['expires_at']}")
        status = "\n".join(lines)
    else:
        status = f"У пользователя {target_id} нет активных подписок."

    await message.answer(status)

# ========== НОВАЯ АДМИНСКАЯ КОМАНДА ДЛЯ ПОДАРКА ==========
@router.message(Command("gift_premium"))
async def cmd_gift_premium(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет прав.")
        return
    args = message.text.split()
    if len(args) < 4:
        await message.answer("❌ Использование: /gift_premium <to_user_id> <subject> <days>")
        return
    try:
        to_user = int(args[1])
        subject = args[2]
        days = int(args[3])
    except:
        await message.answer("❌ Неверный формат.")
        return
    expires = db.gift_subject_premium(message.from_user.id, to_user, subject, days)
    await message.answer(f"✅ Подарок отправлен пользователю {to_user} на {days} дней по предмету {subject} (до {expires})")

# ========== КОМАНДЫ РАССЫЛКИ ==========

async def _do_broadcast(message: Message, text: str, opt_in_only: bool):
    """Внутренняя функция рассылки с rate limiting и обработкой ошибок."""
    user_ids = db.get_all_user_ids(opt_in_only=opt_in_only)
    total = len(user_ids)
    sent = 0
    failed = 0
    start_ts = time.monotonic()

    await message.answer(
        f"📢 Начинаю рассылку...\n"
        f"Получателей: {total} {'(подписанных на новости)' if opt_in_only else '(все пользователи)'}"
    )

    for i, uid in enumerate(user_ids):
        try:
            await message.bot.send_message(uid, text)
            sent += 1
        except Exception as exc:
            failed += 1
            err_str = str(exc).lower()
            if "blocked" in err_str or "chat not found" in err_str or "deactivated" in err_str:
                logger.info("Broadcast: пользователь %s недоступен (%s)", uid, exc)
            else:
                logger.warning("Broadcast: ошибка отправки %s: %s", uid, exc)

        # Rate limiting: пауза после каждого _BROADCAST_RATE сообщения
        if (i + 1) % _BROADCAST_RATE == 0:
            await asyncio.sleep(1)

    elapsed = time.monotonic() - start_ts
    await message.answer(
        f"✅ Рассылка завершена!\n\n"
        f"📊 Статистика:\n"
        f"• Целевых пользователей: {total}\n"
        f"• Отправлено успешно: {sent}\n"
        f"• Не доставлено: {failed}\n"
        f"• Время: {elapsed:.1f} сек"
    )


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет прав на выполнение этой команды.")
        return

    # /broadcast <сообщение>
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "❌ Использование: /broadcast <текст>\n"
            "Сообщение будет отправлено всем пользователям с включёнными новостями."
        )
        return

    broadcast_text = parts[1].strip()
    await _do_broadcast(message, broadcast_text, opt_in_only=True)


@router.message(Command("broadcast_all"))
async def cmd_broadcast_all(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет прав на выполнение этой команды.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "❌ Использование: /broadcast_all <текст>\n"
            "Сообщение будет отправлено ВСЕМ пользователям (независимо от настроек новостей)."
        )
        return

    broadcast_text = parts[1].strip()
    await _do_broadcast(message, broadcast_text, opt_in_only=False)
