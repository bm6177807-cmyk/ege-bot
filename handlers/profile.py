import logging

logger = logging.getLogger(__name__)

async def pay_stars(...):
    logger.info('Entering pay_stars function')
    try:
        await bot.send_invoice(...)
    except Exception as e:
        logger.error(f'Error sending invoice: {e}')
        await message.answer('Sorry, there was an error processing your payment. Please try again later.')

async def handle_pre_checkout(...):
    logger.info('Entering handle_pre_checkout function')
    ... # existing code

async def handle_successful_payment(...):
    logger.info('Entered handle_successful_payment function')
    ... # existing code