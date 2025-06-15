import logging
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ConversationHandler
)

from config import BOT_TOKEN, MENU, CART, CHECKOUT, PHONE, ADDRESS, CONFIRMATION, PAYMENT, ORDER_STATUS
from handlers.start import start, cancel
from handlers.menu import menu_handler
from handlers.cart import cart_handler, cart_update
from handlers.checkout import checkout_handler, phone_handler, address_handler, confirmation_handler
from handlers.admin import admin_response_handler
from handlers.payment import payment_handler, process_payment
from handlers.order import order_status_handler, cancel_order_handler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [
                CallbackQueryHandler(menu_handler, pattern='^(menu|category_|item_|add_to_cart_|back_to_main)'),
                CallbackQueryHandler(cart_handler, pattern='^cart$'),
                CallbackQueryHandler(cancel_order_handler, pattern='^cancel_order_')
            ],
            CART: [
                CallbackQueryHandler(cart_update, pattern='^(add_|remove_|clear_cart|checkout)'),
                CallbackQueryHandler(menu_handler, pattern='^menu$'),
                CallbackQueryHandler(cancel_order_handler, pattern='^cancel_order_')
            ],
            CHECKOUT: [
                # This state is mostly a transition state
            ],
            PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, phone_handler)
            ],
            ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, address_handler)
            ],
            CONFIRMATION: [
                CallbackQueryHandler(confirmation_handler, pattern='^(confirm_order|cancel_order)'),
                CallbackQueryHandler(menu_handler, pattern='^menu$')
            ],
            PAYMENT: [
                CallbackQueryHandler(payment_handler, pattern='^(pay_|cancel_payment)'),
                CallbackQueryHandler(process_payment, pattern='^payment_complete_'),
                CallbackQueryHandler(menu_handler, pattern='^menu$'),
                CallbackQueryHandler(cancel_order_handler, pattern='^cancel_order_')
            ],
            ORDER_STATUS: [
                CallbackQueryHandler(order_status_handler, pattern='^check_status_'),
                CallbackQueryHandler(cancel_order_handler, pattern='^cancel_order_'),
                CallbackQueryHandler(menu_handler, pattern='^menu$')
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        per_chat=False,
        per_user=True,
        name="food_delivery_conversation"
    )

    application.add_handler(conv_handler)

    # Глобальные обработчики callback-запросов для админских действий
    application.add_handler(CallbackQueryHandler(
        admin_response_handler, pattern='^admin_(approve|reject|preparing|delivering|complete)_'
    ))

    # Глобальный обработчик для меню и корзины (чтобы кнопки работали всегда)
    application.add_handler(CallbackQueryHandler(menu_handler, pattern='^menu$'))
    application.add_handler(CallbackQueryHandler(cart_handler, pattern='^cart$'))

    # Start the Bot
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == '__main__':
    main()

