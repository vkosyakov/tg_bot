import logging
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import MENU, PAYMENT, ADMIN_GROUP_ID
from utils.helpers import get_main_menu_keyboard, get_cart_total
from utils.database import get_order, update_order_status

logger = logging.getLogger(__name__)


async def payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle payment processing."""
    query = update.callback_query
    await query.answer()

    logger.info(f"Обработка платежа: {query.data}")

    if query.data.startswith('pay_'):
        order_id = query.data.split('_')[1]

        # Получаем информацию о заказе
        order_data = get_order(order_id)

        if not order_data:
            await query.edit_message_text(
                "Заказ не найден или устарел.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Вернуться в меню", callback_data='menu')]
                ])
            )
            return MENU

        # Рассчитываем сумму заказа
        total = get_cart_total(order_data.get('cart', {}))

        # Генерируем "платежную ссылку" (для демонстрации)
        payment_link = f"https://vkosyakov.github.io/skills-github-pages/   ?order={order_id}&amount={total}"

        # Для демонстрации просто отправляем платежную ссылку
        # В реальном проекте здесь была бы интеграция с платежной системой
        keyboard = [
            [InlineKeyboardButton("✅ Я оплатил заказ", callback_data=f'payment_complete_{order_id}')],
            [InlineKeyboardButton("❌ Отменить заказ", callback_data=f'cancel_order_{order_id}')]
        ]

        await query.edit_message_text(
            f"Для завершения оформления заказа, пожалуйста, оплатите {total}₽.\n\n"
            f"Ссылка для оплаты: {payment_link}\n\n"
            f"После оплаты нажмите кнопку 'Я оплатил заказ'.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return PAYMENT

    elif query.data == 'cancel_payment':
        await query.edit_message_text(
            "Оплата отменена.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Вернуться в меню", callback_data='menu')]
            ])
        )
        return MENU

    return PAYMENT


async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process payment completion."""
    query = update.callback_query
    await query.answer()

    logger.info(f"Обработка завершения платежа: {query.data}")

    if query.data.startswith('payment_complete_'):
        order_id = query.data.split('_')[2]

        # Получаем информацию о заказе
        order_data = get_order(order_id)

        if not order_data:
            await query.edit_message_text(
                "Заказ не найден или устарел.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Вернуться в меню", callback_data='menu')]
                ])
            )
            return MENU

        # Обновляем статус заказа
        order_data['status'] = 'paid'
        update_order_status(order_id, 'paid')

        # Обновляем сообщение у пользователя
        await query.edit_message_text(
            "Спасибо за оплату! Ваш заказ передан на кухню и скоро будет готов.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Вернуться в меню", callback_data='menu')]
            ])
        )

        # Отправляем уведомление в группу администраторов
        try:
            # Находим ID сообщения в группе админов
            admin_message_info = next(
                (msg for msg in order_data.get('message_ids', []) if str(msg.get('chat_id')) == str(ADMIN_GROUP_ID)),
                None
            )

            if admin_message_info:
                # Обновляем сообщение в группе админов
                await context.bot.edit_message_text(
                    chat_id=admin_message_info['chat_id'],
                    message_id=admin_message_info['message_id'],
                    text=f"💰 ЗАКАЗ ОПЛАЧЕН 💰\n\n"
                         f"ID заказа: {order_id}\n"
                         f"Клиент: {order_data.get('full_name')}"
                         f"{' (@' + order_data.get('username') + ')' if order_data.get('username') else ''}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🍳 Начать готовить", callback_data=f'admin_preparing_{order_id}')]
                    ])
                )
            else:
                # Если не нашли сообщение, отправляем новое
                await context.bot.send_message(
                    chat_id=ADMIN_GROUP_ID,
                    text=f"💰 ЗАКАЗ ОПЛАЧЕН 💰\n\n"
                         f"ID заказа: {order_id}\n"
                         f"Клиент: {order_data.get('full_name')}"
                         f"{' (@' + order_data.get('username') + ')' if order_data.get('username') else ''}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🍳 Начать готовить", callback_data=f'admin_preparing_{order_id}')]
                    ])
                )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления об оплате заказа: {e}")
            logger.error(traceback.format_exc())

        return MENU

    return PAYMENT