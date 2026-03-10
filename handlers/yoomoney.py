# handlers/yoomoney.py
import os
import uuid
import logging
from urllib.parse import urlencode

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

import database as db

router = Router()
logger = logging.getLogger(__name__)

# Subscription prices in RUB
PRICES_RUB = {30: 300, 90: 750, 180: 1200}


def _build_quickpay_url(receiver: str, amount: int, label: str, targets: str, success_url: str | None = None) -> str:
    params = {
        "receiver": receiver,
        "quickpay-form": "shop",
        "targets": targets,
        "paymentType": "AC",
        "sum": str(amount),
        "label": label,
    }
    if success_url:
        params["successURL"] = success_url
    return "https://yoomoney.ru/quickpay/confirm.xml?" + urlencode(params)


@router.callback_query(F.data.startswith("pay_yoomoney_"))
async def pay_subject_yoomoney(callback: CallbackQuery) -> None:
    """Generate a YooMoney Quickpay link for subject premium purchase."""
    parts = callback.data.split("_")
    # expected format: pay_yoomoney_<subject>_<days>
    if len(parts) != 4:
        await callback.answer("❌ Некорректные данные оплаты", show_alert=True)
        return

    subject = parts[2]
    try:
        days = int(parts[3])
    except ValueError:
        await callback.answer("❌ Некорректный срок подписки", show_alert=True)
        return

    amount = PRICES_RUB.get(days)
    if amount is None:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return

    receiver = os.getenv("YOOMONEY_RECEIVER")
    if not receiver:
        await callback.answer("❌ YooMoney не настроен (отсутствует YOOMONEY_RECEIVER)", show_alert=True)
        return

    public_base_url = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    success_url = f"{public_base_url}/" if public_base_url else None

    order_id = str(uuid.uuid4())
    db.save_pending_payment(order_id, callback.from_user.id, subject, days)

    pay_url = _build_quickpay_url(
        receiver=receiver,
        amount=amount,
        label=order_id,
        targets=f"Премиум {subject} на {days} дней",
        success_url=success_url,
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить через ЮMoney", url=pay_url)],
        [InlineKeyboardButton(text="← Назад", callback_data=f"pay_subject_{subject}_{days}")],
    ])

    await callback.message.edit_text(
        f"💰 <b>Оплата через ЮMoney</b>\n\n"
        f"Предмет: <b>{subject}</b>\n"
        f"Срок: <b>{days} дней</b>\n"
        f"Сумма: <b>{amount} ₽</b>\n\n"
        f"После оплаты подписка активируется автоматически (обычно в течение минуты).",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await callback.answer()


async def handle_yoomoney_webhook(request: web.Request) -> web.Response:
    """
    aiohttp handler for YooMoney payment notifications.
    Expects form-urlencoded POST data; uses the `label` field as order_id.
    Minimal security: shared secret in X-Yoomoney-Secret header.
    """
    try:
        secret = os.getenv("YOOMONEY_WEBHOOK_SECRET")
        if secret:
            provided = request.headers.get("X-Yoomoney-Secret", "")
            if provided != secret:
                logger.warning("YooMoney webhook: invalid secret")
                return web.Response(text="forbidden", status=403)

        data = await request.post()
        label = data.get("label", "").strip()
        status = data.get("status", data.get("notification_type", "")).lower()

        logger.info("YooMoney webhook: status=%s label=%s", status, label)

        if not label:
            return web.Response(text="no label", status=400)

        payment = db.get_pending_payment(label)
        if not payment:
            # Already processed or unknown order
            return web.Response(text="ok", status=200)

        # Only activate on successful payment statuses.
        # YooMoney sends "success" for wallet payments and "payment-succeeded" for card payments.
        # The "paid" value is included for forward compatibility.
        ok_statuses = {"success", "paid", "payment-succeeded"}
        if status and status not in ok_statuses:
            return web.Response(text="ignored", status=200)

        db.set_subject_premium(payment["user_id"], payment["subject"], payment["days"])
        db.delete_pending_payment(label)
        logger.info(
            "YooMoney: activated premium user_id=%s subject=%s days=%s",
            payment["user_id"], payment["subject"], payment["days"],
        )
        return web.Response(text="ok", status=200)
    except Exception:
        logger.exception("YooMoney webhook error")
        return web.Response(text="error", status=500)
