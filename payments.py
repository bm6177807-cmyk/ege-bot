# handlers/payments.py
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext

import database as db
from keyboards import kb_main, kb_profile_menu

router = Router()

# Цена в Telegram Stars (300 ≈ 300 Stars)
PREMIUM_MONTH_PRICE = 300

@router.callback_query(F.data == "premium")
async def show_premium_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню премиум-подписки"""
    await callback.message.delete()
    
    user_id = callback.from_user.id
    has_premium = db.has_premium(user_id)
    sub_info = db.get_subscription(user_id)
    
    text = "🌟 **Премиум-доступ** 🌟\n\n"
    
    if has_premium:
        text += f"✅ У вас уже есть активная подписка до {sub_info['expires_at']}\n\n"
        text += "Хотите продлить?"
    else:
        text += (
            "С премиумом ты получаешь:\n"
            "✅ Полный доступ ко всем темам\n"
            "✅ Неограниченное количество заданий\n"
            "✅ PDF-конспекты\n"
            "✅ Генерацию заданий через ИИ\n"
            "✅ Приоритетную поддержку\n\n"
        )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Купить на месяц ({PREMIUM_MONTH_PRICE} ⭐)", callback_data="buy_premium_month")],
        [InlineKeyboardButton(text="← Назад в профиль", callback_data="back_to_profile")]
    ])
    
    await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "buy_premium_month")
async def buy_premium_month(callback: CallbackQuery, state: FSMContext):
    """Создаёт счёт на оплату премиума на месяц"""
    await callback.message.delete()
    
    prices = [LabeledPrice(label="Премиум на 1 месяц", amount=PREMIUM_MONTH_PRICE)]
    
    await callback.message.answer_invoice(
        title="🌟 Премиум-доступ на 1 месяц",
        description="Полный доступ ко всем функциям бота на 30 дней",
        payload="premium_month",
        provider_token="",  # Для Stars оставляем пустым
        currency="XTR",      # Специальный код для Telegram Stars
        prices=prices,
        start_parameter="premium_month",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Оплатить {PREMIUM_MONTH_PRICE} ⭐", pay=True)],
            [InlineKeyboardButton(text="← Отмена", callback_data="premium")]
        ])
    )
    await callback.answer()

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_q: PreCheckoutQuery):
    """Обязательный обработчик предварительной проверки платежа"""
    await pre_checkout_q.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: Message):
    """Обработка успешного платежа"""
    user_id = message.from_user.id
    payment = message.successful_payment
    payload = payment.invoice_payload
    
    if payload != "premium_month":
        return
    
    expires = (datetime.now() + timedelta(days=30)).date()
    db.set_subscription(user_id, "premium", expires.isoformat())
    
    await message.answer(
        "✅ **Оплата прошла успешно!**\n\n"
        f"Премиум-доступ активирован до {expires.strftime('%d.%m.%Y')}.\n"
        "Спасибо за поддержку проекта! 🌟",
        parse_mode="Markdown"
    )
    
    # Уведомление админу (если указан)
    import os
    admin_id = os.getenv("ADMIN_ID")
    if admin_id:
        try:
            await message.bot.send_message(
                admin_id,
                f"💰 Новый платёж!\n"
                f"Пользователь: @{message.from_user.username} (ID: {user_id})\n"
                f"Сумма: {payment.total_amount} ⭐\n"
                f"Действует до: {expires.strftime('%d.%m.%Y')}"
            )
        except:
            pass

@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: CallbackQuery, state: FSMContext):
    """Возврат в профиль"""
    await callback.message.delete()
    await callback.message.answer("Твой профиль:", reply_markup=kb_profile_menu())
    await callback.answer()
