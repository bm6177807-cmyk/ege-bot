from aiogram import Router
from aiohttp import web
import hmac
import hashlib
import os

router = Router()

@router.callback_query_handler(lambda c: c.data.startswith('pay_subject_'))
async def process_pay_subject(callback_query: types.CallbackQuery):
    subject = callback_query.data.split('_')[2]
    days = callback_query.data.split('_')[3]
    order_id = f'order_{subject}_{days}_{2026-03-10 21:06:25}'
    # Generate YooMoney quickpay URL
    quickpay_url = f'https://yoomoney.ru/quickpay/shop/widget?writer=urn:example&label={order_id}&success=https://ege-bot-2etu.onrender.com&fail=https://ege-bot-2etu.onrender.com'
    await callback_query.answer(text=f'Pay for {subject} for {days} days at {quickpay_url}')

async def handle_yoomoney_webhook(request_json, header_signature):
    secret = os.getenv('YOOMONEY_WEBHOOK_SECRET')
    expected_signature = hmac.new(secret.encode(), request_json.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_signature, header_signature):
        return web.Response(status=403)  # Unauthorized access
    # Activate subject premium
    database.set_subject_premium(request_json['subject']
    # Delete pending payment
    delete_pending_payment(request_json['order_id'])