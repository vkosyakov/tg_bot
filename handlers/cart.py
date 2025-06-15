from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from data.menu import menu_items
from config import MENU, CART
from utils.helpers import format_cart_text
import logging

logger = logging.getLogger(__name__)


async def cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cart operations."""
    query = update.callback_query

    # Обязательно отвечаем на callback-запрос
    if query:
        await query.answer()

        logger.info(f"Обработка корзины. Данные корзины: {context.user_data.get('cart', {})}")

        # Инициализируем корзину, если её нет
        if 'cart' not in context.user_data:
            context.user_data['cart'] = {}

        if not context.user_data.get('cart'):
            # Cart is empty
            try:
                await query.edit_message_text(
                    "Ваша корзина пуста.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 Вернуться в меню", callback_data='menu')]
                    ])
                )
            except Exception as e:
                logger.error(f"Ошибка при обновлении сообщения: {e}")
                await query.message.reply_text(
                    "Ваша корзина пуста.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 Вернуться в меню", callback_data='menu')]
                    ])
                )

            return MENU

        # Display cart contents
        cart_text = format_cart_text(context.user_data['cart'])

        keyboard = []
        for item_id, quantity in context.user_data['cart'].items():
            # Проверяем, существует ли товар в меню
            if item_id in menu_items:
                item = menu_items[item_id]
                keyboard.append([
                    InlineKeyboardButton(f"➖ {item['name']}", callback_data=f'remove_{item_id}'),
                    InlineKeyboardButton(f"➕ {item['name']}", callback_data=f'add_{item_id}')
                ])
            else:
                logger.warning(f"Товар с ID {item_id} не найден в меню")

        keyboard.append([InlineKeyboardButton("🗑️ Очистить корзину", callback_data='clear_cart')])
        keyboard.append([InlineKeyboardButton("✅ Оформить заказ", callback_data='checkout')])
        keyboard.append([InlineKeyboardButton("📋 Вернуться в меню", callback_data='menu')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await query.edit_message_text(cart_text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Ошибка при обновлении сообщения: {e}")
            await query.message.reply_text(cart_text, reply_markup=reply_markup)

        return CART

    return CART


async def cart_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle updates to the cart."""
    from handlers.menu import menu_handler
    from handlers.checkout import checkout_handler

    query = update.callback_query

    # Обязательно отвечаем на callback-запрос
    if query:
        await query.answer()

        logger.info(f"Обновление корзины: {query.data}")

        if query.data.startswith('add_'):
            parts = query.data.split('_')
            if len(parts) >= 2:
                item_id = '_'.join(parts[1:])  # Объединяем части, если в id есть подчеркивания

                if 'cart' not in context.user_data:
                    context.user_data['cart'] = {}

                if item_id in context.user_data['cart']:
                    context.user_data['cart'][item_id] += 1
                else:
                    context.user_data['cart'][item_id] = 1

                logger.info(f"Товар добавлен: {item_id}, количество: {context.user_data['cart'][item_id]}")

            # После обновления возвращаемся в обработчик корзины
            return await cart_handler(update, context)

        elif query.data.startswith('remove_'):
            parts = query.data.split('_')
            if len(parts) >= 2:
                item_id = '_'.join(parts[1:])  # Объединяем части, если в id есть подчеркивания

                if 'cart' in context.user_data and item_id in context.user_data['cart']:
                    if context.user_data['cart'][item_id] > 1:
                        context.user_data['cart'][item_id] -= 1
                        logger.info(
                            f"Уменьшено количество: {item_id}, новое количество: {context.user_data['cart'][item_id]}")
                    else:
                        del context.user_data['cart'][item_id]
                        logger.info(f"Товар удален из корзины: {item_id}")

            # После обновления возвращаемся в обработчик корзины
            return await cart_handler(update, context)

        elif query.data == 'clear_cart':
            context.user_data['cart'] = {}
            logger.info("Корзина очищена")

            try:
                await query.edit_message_text(
                    "Корзина очищена.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 Вернуться в меню", callback_data='menu')]
                    ])
                )
            except Exception as e:
                logger.error(f"Ошибка при обновлении сообщения: {e}")
                await query.message.reply_text(
                    "Корзина очищена.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 Вернуться в меню", callback_data='menu')]
                    ])
                )

            return MENU

        elif query.data == 'checkout':
            return await checkout_handler(update, context)

        elif query.data == 'menu':
            return await menu_handler(update, context)

    # Update cart display
    return await cart_handler(update, context)
