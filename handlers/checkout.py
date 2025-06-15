import logging
import traceback
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from config import MENU, PHONE, ADDRESS, CONFIRMATION, PAYMENT, ORDER_STATUS, ADMIN_GROUP_ID
from utils.helpers import get_order_text, generate_order_id, get_main_menu_keyboard
from utils.database import save_order, update_order_status

logger = logging.getLogger(__name__)


async def checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle checkout process."""
    query = update.callback_query
    await query.answer()

    logger.info("Начало оформления заказа")

    if not context.user_data.get('cart') or not context.user_data['cart']:
        await query.edit_message_text(
            "Ваша корзина пуста, невозможно оформить заказ.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Вернуться в меню", callback_data='menu')]
            ])
        )
        return MENU

    reply_markup = ReplyKeyboardMarkup([['Отменить заказ']], one_time_keyboard=True)
    await query.edit_message_text(
        "Для оформления заказа, пожалуйста, укажите свой номер телефона в формате +7XXXXXXXXXX",
        reply_markup=InlineKeyboardMarkup([])
    )

    await update.effective_message.reply_text(
        "Введите ваш номер телефона:",
        reply_markup=reply_markup
    )

    return PHONE


async def phone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone number input."""
    from handlers.start import start

    if update.message.text == 'Отменить заказ':
        await update.message.reply_text(
            "Заказ отменен.",
            reply_markup=ReplyKeyboardRemove()
        )
        return await start(update, context)

    # Basic phone validation
    phone = update.message.text.strip()
    if not (phone.startswith('+7') and len(phone) == 12 and phone[1:].isdigit()):
        await update.message.reply_text(
            "Неверный формат номера телефона. Пожалуйста, введите номер в формате +7XXXXXXXXXX"
        )
        return PHONE

    # Save phone number
    context.user_data['phone'] = phone
    logger.info(f"Сохранен номер телефона: {phone}")

    # Ask for address
    await update.message.reply_text(
        "Теперь, пожалуйста, введите адрес доставки:",
        reply_markup=ReplyKeyboardMarkup([['Отменить заказ']], one_time_keyboard=True)
    )

    return ADDRESS


async def address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle address input."""
    from handlers.start import start

    if update.message.text == 'Отменить заказ':
        await update.message.reply_text(
            "Заказ отменен.",
            reply_markup=ReplyKeyboardRemove()
        )
        return await start(update, context)

    # Save address
    address = update.message.text.strip()
    if len(address) < 5:
        await update.message.reply_text(
            "Адрес слишком короткий. Пожалуйста, укажите полный адрес доставки."
        )
        return ADDRESS

    context.user_data['address'] = address
    logger.info(f"Сохранен адрес: {address}")

    # Show order summary
    order_text = get_order_text(
        context.user_data['cart'],
        context.user_data['phone'],
        context.user_data['address']
    )

    order_text += "\n\nПодтвердить заказ?"

    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data='confirm_order')],
        [InlineKeyboardButton("❌ Отменить", callback_data='cancel_order')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        order_text,
        reply_markup=reply_markup
    )

    return CONFIRMATION


async def confirmation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle order confirmation."""
    query = update.callback_query
    await query.answer()

    logger.info(f"Обработка подтверждения заказа: {query.data}")

    if query.data == 'cancel_order':
        await query.edit_message_text(
            "Заказ отменен.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Вернуться в меню", callback_data='menu')]
            ])
        )
        return MENU

    elif query.data == 'confirm_order':
        try:
            # Generate order ID
            order_id = generate_order_id()
            context.user_data['current_order_id'] = order_id
            logger.info(f"Создан ID заказа: {order_id}")

            # Сохраняем данные заказа
            user = update.effective_user
            order_data = {
                'user_id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'cart': context.user_data['cart'],
                'phone': context.user_data['phone'],
                'address': context.user_data['address'],
                'status': 'pending',
                'message_ids': [],  # ID сообщений для обновления
                'timestamp': int(order_id)
            }

            # Сохраняем заказ в базе данных
            save_order(order_id, order_data)

            # Сохраняем в bot_data для быстрого доступа
            context.bot_data.setdefault('orders', {})
            context.bot_data['orders'][order_id] = order_data

            # Prepare order message for admin group
            order_text = "🆕 НОВЫЙ ЗАКАЗ 🆕\n\n"
            order_text += get_order_text(
                context.user_data['cart'],
                context.user_data['phone'],
                context.user_data['address'],
                order_id
            )

            # Add user info
            if user.username:
                order_text += f"\nПользователь: {user.full_name} (@{user.username})"
            else:
                order_text += f"\nПользователь: {user.full_name}"

            # Create approval buttons
            keyboard = [
                [
                    InlineKeyboardButton("✅ Принять", callback_data=f'admin_approve_{order_id}'),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f'admin_reject_{order_id}')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Determine target chat ID
            target_chat_id = ADMIN_GROUP_ID
            if ADMIN_GROUP_ID == "REPLACE_WITH_YOUR_GROUP_ID" or not ADMIN_GROUP_ID.startswith('-'):
                logger.warning("ADMIN_GROUP_ID не настроен или имеет неверный формат")
                # Для демонстрации отправляем заказ самому пользователю
                target_chat_id = update.effective_user.id

            # Send to admin group
            logger.info(f"Отправка заказа в чат {target_chat_id}")
            admin_message = await context.bot.send_message(
                chat_id=target_chat_id,
                text=order_text,
                reply_markup=reply_markup
            )

            # Сохраняем ID сообщения в группе для будущих обновлений
            order_data['message_ids'].append({
                'chat_id': target_chat_id,
                'message_id': admin_message.message_id
            })
            save_order(order_id, order_data)

            # Notify user about successful order
            success_message = (
                "✅ Ваш заказ оформлен и отправлен на подтверждение администратору.\n\n"
                "Вы получите уведомление, когда заказ будет подтвержден или отклонен.\n\n"
                "Спасибо за заказ!"
            )

            await query.edit_message_text(success_message)

            # Добавляем кнопку для отмены заказа
            cancel_keyboard = [
                [InlineKeyboardButton("❌ Отменить заказ", callback_data=f'cancel_order_{order_id}')]
            ]
            cancel_markup = InlineKeyboardMarkup(cancel_keyboard)

            status_message = await query.message.reply_text(
                f"Статус вашего заказа: Ожидает подтверждения\n"
                f"ID заказа: {order_id}",
                reply_markup=cancel_markup
            )

            # Сохраняем ID сообщения у пользователя для будущих обновлений
            order_data['message_ids'].append({
                'chat_id': user.id,
                'message_id': status_message.message_id
            })
            save_order(order_id, order_data)

            # Clear the cart
            context.user_data['cart'] = {}

            # Отправляем главное меню
            await send_main_menu(context.bot, update.effective_user.id)

            return ORDER_STATUS

        except Exception as e:
            logger.error(f"Ошибка при обработке заказа: {e}")
            logger.error(traceback.format_exc())

            await query.edit_message_text(
                "Произошла ошибка при оформлении заказа. Пожалуйста, попробуйте позже.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Вернуться в меню", callback_data='menu')]
                ])
            )

            return MENU


async def send_main_menu(bot, user_id):
    """Send main menu to user."""
    try:
        await bot.send_message(
            chat_id=user_id,
            text="Что бы вы хотели сделать дальше?",
            reply_markup=get_main_menu_keyboard()
        )
        logger.info(f"Пользователь {user_id} возвращен в главное меню")
    except Exception as e:
        logger.error(f"Ошибка при отправке главного меню: {e}")
        logger.error(traceback.format_exc())
