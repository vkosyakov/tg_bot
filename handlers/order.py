import logging
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import MENU, ORDER_STATUS, ADMIN_GROUP_ID
from utils.helpers import get_main_menu_keyboard
from utils.database import get_order, update_order_status

logger = logging.getLogger(__name__)


async def order_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle order status check."""
    query = update.callback_query
    await query.answer()

    logger.info(f"Обработка проверки статуса заказа: {query.data}")

    if query.data.startswith('check_status_'):
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

        status = order_data.get('status', 'pending')
        status_text = {
            'pending': "Ожидает подтверждения",
            'approved': "Подтвержден, ожидает оплаты",
            'paid': "Оплачен, готовится",
            'preparing': "Готовится",
            'delivering': "В доставке",
            'completed': "Доставлен",
            'rejected': "Отклонен",
            'cancelled': "Отменен"
        }.get(status, "Неизвестный статус")

        # Формируем клавиатуру в зависимости от статуса
        keyboard = []

        if status in ['pending', 'approved']:
            keyboard.append([InlineKeyboardButton("❌ Отменить заказ", callback_data=f'cancel_order_{order_id}')])

        keyboard.append([InlineKeyboardButton("📋 Вернуться в меню", callback_data='menu')])

        await query.edit_message_text(
            f"Статус вашего заказа: {status_text}\n"
            f"ID заказа: {order_id}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return ORDER_STATUS

    return MENU


async def cancel_order_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle order cancellation."""
    query = update.callback_query
    await query.answer()

    logger.info(f"Обработка отмены заказа: {query.data}")

    if query.data.startswith('cancel_order_'):
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

        # Проверяем, что заказ принадлежит этому пользователю
        if order_data.get('user_id') != update.effective_user.id:
            await query.answer("Вы не можете отменить этот заказ", show_alert=True)
            return ORDER_STATUS

        # Проверяем, что заказ в статусе, который можно отменить
        if order_data.get('status') not in ['pending', 'approved']:
            await query.answer("Этот заказ уже нельзя отменить", show_alert=True)
            return ORDER_STATUS

        # Обновляем статус заказа
        order_data['status'] = 'cancelled'
        update_order_status(order_id, 'cancelled')

        # Обновляем сообщение у пользователя
        await query.edit_message_text(
            "Ваш заказ был отменен.",
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
                    text=f"⚠️ ЗАКАЗ ОТМЕНЕН КЛИЕНТОМ ⚠️\n\n"
                         f"ID заказа: {order_id}\n"
                         f"Клиент: {order_data.get('full_name')}"
                         f"{' (@' + order_data.get('username') + ')' if order_data.get('username') else ''}",
                    reply_markup=None
                )
            else:
                # Если не нашли сообщение, отправляем новое
                await context.bot.send_message(
                    chat_id=ADMIN_GROUP_ID,
                    text=f"⚠️ ЗАКАЗ ОТМЕНЕН КЛИЕНТОМ ⚠️\n\n"
                         f"ID заказа: {order_id}\n"
                         f"Клиент: {order_data.get('full_name')}"
                         f"{' (@' + order_data.get('username') + ')' if order_data.get('username') else ''}"
                )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления об отмене заказа: {e}")
            logger.error(traceback.format_exc())

        return MENU

    return ORDER_STATUS