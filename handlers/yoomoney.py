import os
import uuid
import logging
from urllib.parse import urlencode

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiohttp import web

import database as db

router = Router()
logger = logging.getLogger(__name__)

YOOMONEY_RECEIVER = os.getenv("YOOMONEY_RECEIVER")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://ege-bot-2etu.onrender.com")

# Prices match the existing structure in lava.py / profile.py
PRICES = {30: 300, 90: 750, 180: 1200}

if not os.getenv("YOOMONEY_WEBHOOK_SECRET"):
    logger.warning(
        "YOOMONEY_WEBHOOK_SECRET не задан — webhook /yoomoney-webhook принимает запросы без проверки подлинности!"
    )


@router.callback_query(F.data.startswith("pay_yoomoney_"))
async def pay_yoomoney_subject(callback: CallbackQuery, state: FSMContext):
    """Создаёт ссылку на оплату через ЮMoney Quickpay и сохраняет pending payment."""
    parts = callback.data.split("_")
    subject = parts[2]
    days = int(parts[3])
    amount = PRICES.get(days, 300)
    order_id = str(uuid.uuid4())

    db.save_pending_payment(order_id, callback.from_user.id, subject, days)
    logger.info(
        f"YooMoney: created pending payment order_id={order_id} "
        f"user={callback.from_user.id} subject={subject} days={days}"
    )

    params = {
        "receiver": YOOMONEY_RECEIVER,
        "quickpay-form": "shop",
        "targets": f"Премиум {subject} {days} дней",
        "paymentType": "AC",
        "sum": amount,
        "label": order_id,
        "successURL": PUBLIC_BASE_URL,
    }
    quickpay_url = "https://yoomoney.ru/quickpay/confirm?" + urlencode(params)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💛 Оплатить через ЮMoney", url=quickpay_url)],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_profile")],
    ])
    await callback.message.edit_text(
        f"💰 **Оплата через ЮMoney**\n\n"
        f"Предмет: **{subject}**\n"
        f"Срок: **{days} дней**\n"
        f"Сумма: **{amount} ₽**\n\n"
        f"Нажмите кнопку, чтобы перейти к оплате.\n"
        f"После успешной оплаты подписка активируется автоматически.",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


async def handle_yoomoney_webhook(request: web.Request) -> web.Response:
    """Обрабатывает входящее уведомление от ЮMoney."""
    secret = os.getenv("YOOMONEY_WEBHOOK_SECRET")
    if secret:
        header_secret = request.headers.get("X-Yoomoney-Secret", "")
        if header_secret != secret:
            logger.warning("YooMoney webhook: неверный секрет, запрос отклонён")
            return web.Response(status=403)

    try:
        data = await request.post()
        label = data.get("label", "")
        notification_type = data.get("notification_type", "")

        if not label:
            logger.warning("YooMoney webhook: отсутствует поле label")
            return web.Response(text="Bad Request", status=400)

        # Only process completed incoming payments
        if notification_type not in ("payment-received", "card-incoming", ""):
            logger.info(f"YooMoney webhook: пропущен тип уведомления notification_type={notification_type!r}")
            return web.Response(text="OK", status=200)

        payment = db.get_pending_payment(label)
        if not payment:
            logger.warning(f"YooMoney webhook: pending payment не найден для label={label}")
            return web.Response(text="OK", status=200)

        expires = db.set_subject_premium(payment["user_id"], payment["subject"], payment["days"])
        logger.info(
            f"YooMoney: активирован премиум для user={payment['user_id']} "
            f"subject={payment['subject']} days={payment['days']} до {expires}"
        )
        db.delete_pending_payment(label)
        return web.Response(text="OK", status=200)
    except Exception as e:
        logger.exception(f"YooMoney webhook error: {e}")
        return web.Response(text="Error", status=500)