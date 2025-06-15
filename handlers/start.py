from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from utils.helpers import get_main_menu_keyboard
from config import MENU
import logging

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and display the main menu."""
    user = update.effective_user

    # Initialize user cart if not exists
    if not context.user_data.get('cart'):
        context.user_data['cart'] = {}

    await update.message.reply_text(
        f"Привет, {user.first_name}! Добро пожаловать в бот доставки еды. "
        "Что бы вы хотели сделать?",
        reply_markup=get_main_menu_keyboard()
    )

    return MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel and end the conversation."""
    await update.message.reply_text(
        "Операция отменена.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def return_to_main_menu(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return user to main menu after a delay."""
    try:
        user_id = context.job.data['user_id']

        await context.bot.send_message(
            chat_id=user_id,
            text="Что бы вы хотели сделать дальше?",
            reply_markup=get_main_menu_keyboard()
        )
        logger.info(f"Пользователь {user_id} возвращен в главное меню")
    except Exception as e:
        logger.error(f"Ошибка при возврате в главное меню: {e}")

