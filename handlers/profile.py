import logging

logger = logging.getLogger(__name__)

# ... other code ...

def pay_stars(user_id, subject, days, stars):
    logger.info('Entering pay_stars with user_id: %s, subject: %s, days: %s, stars: %s', user_id, subject, days, stars)
    try:
        bot.send_invoice(
            ... # parameters for send_invoice
        )
    except Exception as e:
        logger.exception('Failed to send invoice for user_id: %s', user_id)
        # send a user-facing error message
        bot.send_message(user_id, 'There was an error processing your payment. Please try again later.')

# Assuming handle_pre_checkout and handle_successful_payment functions exist

def handle_pre_checkout(...):
    logger.info('Handling pre-checkout')
    # existing processing code...


def handle_successful_payment(...):
    logger.info('Handling successful payment')
    # existing processing code...