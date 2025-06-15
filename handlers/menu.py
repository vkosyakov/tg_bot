from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from data.menu import menu_items, categories
from config import MENU
from utils.helpers import get_main_menu_keyboard
import logging

logger = logging.getLogger(__name__)


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle menu navigation and item selection."""
    query = update.callback_query

    # Обязательно отвечаем на callback-запрос
    if query:
        await query.answer()

        # Логируем данные для отладки
        logger.info(f"Получен callback: {query.data}")

        if query.data == 'menu':
            # Show menu categories
            keyboard = []
            for category_id, category_name in categories.items():
                keyboard.append([InlineKeyboardButton(category_name, callback_data=f'category_{category_id}')])

            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')])
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await query.edit_message_text("Выберите категорию:", reply_markup=reply_markup)
            except Exception as e:
                logger.error(f"Ошибка при обновлении сообщения: {e}")
                await query.message.reply_text("Выберите категорию:", reply_markup=reply_markup)

            return MENU

        elif query.data.startswith('category_'):
            category = query.data.split('_')[1]
            # Show items in the selected category
            keyboard = []
            for item_id, item_data in menu_items.items():
                if item_id.startswith(category):
                    keyboard.append([InlineKeyboardButton(
                        f"{item_data['name']} - {item_data['price']}₽",
                        callback_data=f'item_{item_id}'
                    )])

            keyboard.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data='menu')])
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await query.edit_message_text(f"Выберите блюдо из категории:", reply_markup=reply_markup)
            except Exception as e:
                logger.error(f"Ошибка при обновлении сообщения: {e}")
                await query.message.reply_text(f"Выберите блюдо из категории:", reply_markup=reply_markup)

            return MENU

        elif query.data.startswith('item_'):
            item_id = query.data.split('_', 1)[1]
            item = menu_items[item_id]

            # Show item details with add to cart option
            keyboard = [
                [InlineKeyboardButton("🛒 Добавить в корзину", callback_data=f'add_to_cart_{item_id}')],
                [InlineKeyboardButton("🔙 Назад к меню", callback_data='menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await query.edit_message_text(
                    f"*{item['name']}*\n"
                    f"Цена: {item['price']}₽\n"
                    f"Описание: {item['description']}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Ошибка при обновлении сообщения: {e}")
                await query.message.reply_text(
                    f"*{item['name']}*\n"
                    f"Цена: {item['price']}₽\n"
                    f"Описание: {item['description']}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )

            return MENU

        elif query.data.startswith('add_to_cart_'):
            # Важно: не используем жёсткие индексы в split
            parts = query.data.split('_')
            if len(parts) >= 4:
                item_id = '_'.join(parts[3:])  # Обработка случая, если в id есть подчеркивания
            else:
                item_id = parts[-1]  # Берем последний элемент

            logger.info(f"Добавление в корзину: {item_id}")

            # Инициализируем корзину, если её нет
            if 'cart' not in context.user_data:
                context.user_data['cart'] = {}

            # Add item to cart
            if item_id in context.user_data['cart']:
                context.user_data['cart'][item_id] += 1
            else:
                context.user_data['cart'][item_id] = 1

            logger.info(f"Состояние корзины после добавления: {context.user_data['cart']}")

            try:
                await query.edit_message_text(
                    f"{menu_items[item_id]['name']} добавлен в корзину!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🛒 Перейти в корзину", callback_data='cart')],
                        [InlineKeyboardButton("📋 Вернуться в меню", callback_data='menu')]
                    ])
                )
            except Exception as e:
                logger.error(f"Ошибка при обновлении сообщения: {e}")
                await query.message.reply_text(
                    f"{menu_items[item_id]['name']} добавлен в корзину!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🛒 Перейти в корзину", callback_data='cart')],
                        [InlineKeyboardButton("📋 Вернуться в меню", callback_data='menu')]
                    ])
                )

            return MENU

        elif query.data == 'back_to_main':
            # Go back to main menu
            try:
                await query.edit_message_text(
                    "Что бы вы хотели сделать?",
                    reply_markup=get_main_menu_keyboard()
                )
            except Exception as e:
                logger.error(f"Ошибка при обновлении сообщения: {e}")
                await query.message.reply_text(
                    "Что бы вы хотели сделать?",
                    reply_markup=get_main_menu_keyboard()
                )

            return MENU
    return MENU

