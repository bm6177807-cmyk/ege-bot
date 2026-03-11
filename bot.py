import asyncio
import hashlib
import hmac
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from aiohttp import web

from logger_config import setup_logging
import database as db
from handlers import (
    common_router,
    subjects_router,
    tasks_router,
    exam_router,
    profile_router,
    elements_router,
    cheatsheets_router,
    photo_router,
    admin_router,
    achievements_router,
    repetition_router,
    referral_router,
    adaptive_router,
    daily_challenge_router,
    tools_router,
    daily_router,
    mistakes_router,
    progress_router,
    mini_exam_router,
    exam_numbers_router,
)
from handlers.profile import _give_referral_bonus, subject_name

setup_logging()
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env")

YOOMONEY_WEBHOOK_SECRET = os.getenv("YOOMONEY_WEBHOOK_SECRET", "")
PORT = int(os.getenv("PORT", "10000"))

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

db.init_db()
db.init_achievements()

dp.include_router(common_router)
dp.include_router(subjects_router)
dp.include_router(tasks_router)
dp.include_router(exam_router)
dp.include_router(profile_router)
dp.include_router(elements_router)
dp.include_router(cheatsheets_router)
dp.include_router(photo_router)
dp.include_router(admin_router)
dp.include_router(achievements_router)
dp.include_router(repetition_router)
dp.include_router(referral_router)
dp.include_router(adaptive_router)
dp.include_router(daily_challenge_router)
dp.include_router(tools_router)
dp.include_router(daily_router)
dp.include_router(mistakes_router)
dp.include_router(progress_router)
dp.include_router(mini_exam_router)
dp.include_router(exam_numbers_router)


def _verify_yoomoney_signature(data: dict, secret: str) -> bool:
    """Verify YooMoney HTTP-notification SHA-1 signature.

    YooMoney computes:
        sha1(notification_type&operation_id&amount&currency&datetime&sender&codepro&secret_key&label)
    """
    string_to_hash = "&".join([
        data.get("notification_type", ""),
        data.get("operation_id", ""),
        data.get("amount", ""),
        data.get("currency", ""),
        data.get("datetime", ""),
        data.get("sender", ""),
        data.get("codepro", ""),
        secret,
        data.get("label", ""),
    ])
    expected = hashlib.sha1(string_to_hash.encode("utf-8")).hexdigest()
    received = data.get("sha1_hash", "")
    return hmac.compare_digest(expected, received)


# ========== ВЕБ-СЕРВЕР ==========
async def handle_health(request):
    return web.Response(text="OK", status=200)


async def handle_root(request):
    return web.Response(
        text="<html><body><h1>Бот работает</h1></body></html>",
        content_type="text/html",
        status=200,
    )


async def handle_yoomoney_webhook(request):
    """YooMoney HTTP-notification webhook with SHA-1 signature verification."""
    try:
        data = dict(await request.post())
        logger.info(
            f"YooMoney webhook received: notification_type={data.get('notification_type')}, "
            f"label={data.get('label')}"
        )

        # Verify signature when a secret is configured
        if YOOMONEY_WEBHOOK_SECRET:
            if not _verify_yoomoney_signature(data, YOOMONEY_WEBHOOK_SECRET):
                logger.warning("YooMoney webhook: invalid SHA-1 signature")
                return web.Response(text="Forbidden", status=403)
        else:
            logger.warning("YOOMONEY_WEBHOOK_SECRET is not set — skipping signature check")

        label = data.get("label", "")
        unaccepted = data.get("unaccepted", "true")

        if label and unaccepted == "false":
            payment = db.get_pending_payment(label)
            if payment:
                expires = db.set_subject_premium(
                    payment["user_id"], payment["subject"], payment["days"]
                )
                await _give_referral_bonus(bot, payment["user_id"])
                name = subject_name(payment["subject"])
                try:
                    await bot.send_message(
                        payment["user_id"],
                        f"✅ Оплата через YooMoney прошла успешно!\n"
                        f"Премиум на **{name}** активирован на {payment['days']} дней (до {expires}).",
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    logger.error(f"Не удалось уведомить пользователя {payment['user_id']}: {e}")
                db.delete_pending_payment(label)
                logger.info(f"YooMoney: premium activated for user {payment['user_id']} ({name}, {payment['days']} days)")
            else:
                logger.warning(f"YooMoney webhook: pending payment not found for label={label}")

        return web.Response(text="OK", status=200)
    except Exception as e:
        logger.exception(f"YooMoney webhook error: {e}")
        return web.Response(text="Error", status=500)


async def run_web_server():
    app = web.Application()
    app.router.add_get("/health", handle_health)
    app.router.add_get("/healthcheck", handle_health)
    app.router.add_get("/", handle_root)
    app.router.add_post("/yoomoney-webhook", handle_yoomoney_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"✅ Web server started on port {PORT}")


async def reminder_worker():
    while True:
        now = datetime.now().strftime("%H:%M")
        reminders = db.get_active_reminders()
        for user_id, time_str in reminders:
            if time_str == now:
                try:
                    await bot.send_message(user_id, "🔔 Напоминание: пора позаниматься подготовкой к ЕГЭ!")
                except Exception as e:
                    logger.error(f"Не удалось отправить напоминание пользователю {user_id}: {e}")
        await asyncio.sleep(60)


async def main():
    asyncio.create_task(run_web_server())
    asyncio.create_task(reminder_worker())
    logger.info("🚀 Бот запущен")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
