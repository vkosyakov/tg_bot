from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from utils.database import update_order_status
from utils.order_finder import find_order_by_any_identifier  # Импортируем новую функцию

logger = logging.getLogger(__name__)


async def admin_response_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Диагностический код - получить все заказы в базе данных
    try:
        from utils.database import get_all_orders
        all_orders = get_all_orders(limit=5)  # Получить последние 5 заказов
        logger.info("Существующие заказы в базе данных:")
        for i, order in enumerate(all_orders):
            logger.info(f"Заказ {i + 1}: ID={order.get('id')}, номер={order.get('order_number')}, " +
                        f"пользователь={order.get('telegram_id')}, статус={order.get('status')}")
    except Exception as e:
        logger.error(f"Ошибка при получении всех заказов: {e}")

    """Handle admin responses to orders."""
    query = update.callback_query
    await query.answer()

    logger.info(f"Обработка ответа администратора: {query.data}")

    # Получаем действие и ID заказа
    data = query.data.split('_')
    if len(data) < 3:
        logger.error(f"Неверный формат callback-данных: {query.data}")
        return

    action = data[1]  # approve, reject, preparing, delivering, complete
    order_id = data[2]

    logger.info(f"Получены callback-данные: {query.data}")
    logger.info(f"Получен order_id: {order_id}")

    # Используем новую функцию для поиска заказа
    order_data = find_order_by_any_identifier(order_id)

    if not order_data:
        logger.error(f"Заказ с идентификатором {order_id} не найден")
        await query.edit_message_text(
            f"Ошибка: заказ с ID {order_id} не найден. Проверьте, что заказ существует и данные корректны.",
            reply_markup=None
        )
        return

    # Получаем telegram_id пользователя для отправки уведомлений
    telegram_id = order_data.get('telegram_id')

    # Формируем информацию о клиенте
    full_name = f"{order_data.get('first_name', '')} {order_data.get('last_name', '')}".strip()
    username = order_data.get('username', '')

    # Обрабатываем различные действия администратора
    if action == 'approve':
        # Подтверждение заказа
        updated_order = update_order_status(order_data['id'], 'approved')
        if not updated_order:
            logger.error(f"Не удалось обновить статус заказа {order_id}")
            await query.edit_message_text(
                f"Ошибка: не удалось обновить статус заказа {order_id}",
                reply_markup=None
            )
            return

        # Обновляем сообщение в группе администраторов
        keyboard = [
            [InlineKeyboardButton("💰 Ожидание оплаты", callback_data=f'admin_info_{order_id}')]
        ]
        await query.edit_message_text(
            f"✅ ЗАКАЗ ПОДТВЕРЖДЕН ✅\n\n"
            f"Номер заказа: {order_data.get('order_number')}\n"
            f"Клиент: {full_name}"
            f"{' (@' + username + ')' if username else ''}\n\n"
            f"Ожидается оплата от клиента.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # Отправляем пользователю сообщение о подтверждении заказа и ссылку для оплаты
        if telegram_id:
            try:
                # Уведомляем пользователя о подтверждении заказа
                message = await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"🎉 Ваш заказ #{order_data.get('order_number')} подтвержден!\n\n"
                         f"Для продолжения, пожалуйста, оплатите заказ.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💳 Оплатить заказ",
                                              callback_data=f'pay_{order_data.get("order_number")}')],
                        [InlineKeyboardButton("❌ Отменить заказ",
                                              callback_data=f'cancel_order_{order_data.get("order_number")}')]
                    ])
                )

                logger.info(f"Отправлено уведомление о подтверждении заказа пользователю {telegram_id}")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления пользователю: {e}")

    elif action == 'reject':
        # Отклонение заказа
        updated_order = update_order_status(order_data['id'], 'rejected')
        if not updated_order:
            logger.error(f"Не удалось обновить статус заказа {order_id}")
            await query.edit_message_text(
                f"Ошибка: не удалось обновить статус заказа {order_id}",
                reply_markup=None
            )
            return

        await query.edit_message_text(
            f"❌ ЗАКАЗ ОТКЛОНЕН ❌\n\n"
            f"Номер заказа: {order_data.get('order_number')}\n"
            f"Клиент: {full_name}"
            f"{' (@' + username + ')' if username else ''}",
            reply_markup=None
        )

        # Отправляем пользователю сообщение об отклонении заказа
        if telegram_id:
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text="❌ К сожалению, ваш заказ был отклонен администратором. "
                         "Возможные причины: зона доставки, загруженность или технические проблемы. "
                         "Пожалуйста, попробуйте оформить заказ позже или свяжитесь с нами по телефону.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 Вернуться в меню", callback_data='menu')]
                    ])
                )
                logger.info(f"Отправлено уведомление об отклонении заказа пользователю {telegram_id}")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления пользователю: {e}")

    elif action == 'preparing':
        # Заказ начали готовить
        updated_order = update_order_status(order_data['id'], 'preparing')
        if not updated_order:
            logger.error(f"Не удалось обновить статус заказа {order_id}")
            await query.edit_message_text(
                f"Ошибка: не удалось обновить статус заказа {order_id}",
                reply_markup=None
            )
            return

        await query.edit_message_text(
            f"👨‍🍳 ЗАКАЗ ГОТОВИТСЯ 👨‍🍳\n\n"
            f"Номер заказа: {order_data.get('order_number')}\n"
            f"Клиент: {full_name}"
            f"{' (@' + username + ')' if username else ''}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚚 Отправить в доставку", callback_data=f'admin_delivering_{order_id}')]
            ])
        )

        # Отправляем пользователю сообщение о начале приготовления
        if telegram_id:
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"👨‍🍳 Хорошие новости! Ваш заказ #{order_data.get('order_number')} начали готовить. "
                         f"Мы сообщим вам, когда он будет передан курьеру."
                )
                logger.info(f"Отправлено уведомление о приготовлении заказа пользователю {telegram_id}")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления пользователю: {e}")

    elif action == 'delivering':
        # Заказ отправлен в доставку
        updated_order = update_order_status(order_data['id'], 'delivering')
        if not updated_order:
            logger.error(f"Не удалось обновить статус заказа {order_id}")
            await query.edit_message_text(
                f"Ошибка: не удалось обновить статус заказа {order_id}",
                reply_markup=None
            )
            return

        await query.edit_message_text(
            f"🚚 ЗАКАЗ В ДОСТАВКЕ 🚚\n\n"
            f"Номер заказа: {order_data.get('order_number')}\n"
            f"Клиент: {full_name}"
            f"{' (@' + username + ')' if username else ''}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Заказ доставлен", callback_data=f'admin_complete_{order_id}')]
            ])
        )

        # Отправляем пользователю сообщение о доставке
        if telegram_id:
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"🚚 Ваш заказ #{order_data.get('order_number')} передан курьеру и скоро будет у вас!"
                )
                logger.info(f"Отправлено уведомление о доставке заказа пользователю {telegram_id}")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления пользователю: {e}")

    elif action == 'complete':
        # Заказ доставлен
        updated_order = update_order_status(order_data['id'], 'completed')
        if not updated_order:
            logger.error(f"Не удалось обновить статус заказа {order_id}")
            await query.edit_message_text(
                f"Ошибка: не удалось обновить статус заказа {order_id}",
                reply_markup=None
            )
            return

        await query.edit_message_text(
            f"✅ ЗАКАЗ ДОСТАВЛЕН ✅\n\n"
            f"Номер заказа: {order_data.get('order_number')}\n"
            f"Клиент: {full_name}"
            f"{' (@' + username + ')' if username else ''}",
            reply_markup=None
        )

        # Отправляем пользователю сообщение о завершении заказа
        if telegram_id:
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"✅ Ваш заказ #{order_data.get('order_number')} доставлен! Приятного аппетита!\n\n"
                         f"Будем рады видеть вас снова!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 Вернуться в меню", callback_data='menu')]
                    ])
                )
                logger.info(f"Отправлено уведомление о завершении заказа пользователю {telegram_id}")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления пользователю: {e}")