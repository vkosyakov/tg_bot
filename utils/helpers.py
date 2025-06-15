import logging
import traceback
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from data.menu import menu_items

logger = logging.getLogger(__name__)


def get_main_menu_keyboard():
    """Return the main menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("📋 Меню", callback_data='menu')],
        [InlineKeyboardButton("🛒 Корзина", callback_data='cart')]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_cart_total(cart):
    """Calculate the total price of items in the cart."""
    if not cart:
        logger.warning("[DEBUG] Попытка расчета суммы пустой корзины")
        return 0

    total = 0
    for item_id, quantity in cart.items():
        if item_id in menu_items:
            item = menu_items[item_id]
            total += item['price'] * quantity
        else:
            logger.warning(f"[DEBUG] Товар с ID {item_id} не найден в меню при расчете суммы")
    return total


def format_cart_text(cart):
    """Format the cart contents as a text message."""
    if not cart:
        logger.info("[DEBUG] Форматирование пустой корзины")
        return "Ваша корзина пуста."

    cart_text = "🛒 Ваша корзина:\n\n"
    total = 0

    for item_id, quantity in cart.items():
        if item_id in menu_items:
            item = menu_items[item_id]
            item_total = item['price'] * quantity
            total += item_total
            cart_text += f"{item['name']} x{quantity} = {item_total}₽\n"
        else:
            logger.warning(f"[DEBUG] Товар с ID {item_id} не найден в меню при форматировании корзины")
            cart_text += f"[Неизвестный товар] x{quantity}\n"

    cart_text += f"\nИтого: {total}₽"
    return cart_text


def get_order_text(cart, phone, address, order_id=None):
    """Format order information as text."""
    try:
        logger.info(f"[DEBUG] Формирование текста заказа. Товаров в корзине: {len(cart) if cart else 0}")
        logger.info(f"[DEBUG] Телефон: {phone}, Адрес: {address}, ID заказа: {order_id}")

        if not cart:
            logger.warning("[DEBUG] Попытка создания текста заказа с пустой корзиной")
            return "Корзина пуста. Невозможно оформить заказ."

        order_text = "📝 Заказ:\n\n"
        total = 0
        item_count = 0

        for item_id, quantity in cart.items():
            if item_id in menu_items:
                item = menu_items[item_id]
                item_total = item['price'] * quantity
                total += item_total
                order_text += f"{item['name']} x{quantity} = {item_total}₽\n"
                item_count += 1
            else:
                logger.warning(f"[DEBUG] Товар с ID {item_id} не найден в меню при создании текста заказа")
                order_text += f"[Неизвестный товар] x{quantity}\n"

        logger.info(f"[DEBUG] Обработано товаров: {item_count}, Итоговая сумма: {total}₽")

        order_text += f"\nИтого: {total}₽\n\n"

        if not phone:
            logger.warning("[DEBUG] Отсутствует номер телефона при формировании заказа")
            phone = "Не указан"

        if not address:
            logger.warning("[DEBUG] Отсутствует адрес при формировании заказа")
            address = "Не указан"

        order_text += f"Телефон: {phone}\n"
        order_text += f"Адрес: {address}\n"

        if order_id:
            order_text += f"\nID заказа: {order_id}"

        logger.info(f"[DEBUG] Текст заказа успешно сформирован, длина: {len(order_text)} символов")
        return order_text

    except Exception as e:
        logger.error(f"[DEBUG] Ошибка при формировании текста заказа: {e}")
        logger.error(traceback.format_exc())
        # Возвращаем базовое сообщение в случае ошибки
        return "Ошибка при формировании заказа. Пожалуйста, попробуйте позже."


def generate_order_id():
    """Generate a unique order ID."""
    import time
    order_id = str(int(time.time()))
    logger.info(f"[DEBUG] Сгенерирован ID заказа: {order_id}")
    return order_id

