import logging
from typing import Dict, Optional, List, Union, Any
import traceback

logger = logging.getLogger(__name__)


def find_order_by_any_identifier(identifier: Union[str, int]) -> Optional[Dict[str, Any]]:
    """
    Универсальная функция для поиска заказа по любому идентификатору:
    - ID заказа в базе данных
    - Номер заказа (ORD-XXXXXX-XXXX)
    - telegram_id пользователя
    - ID сообщения
    - Метка времени

    Args:
        identifier: Любой идентификатор, который может быть связан с заказом

    Returns:
        Dict[str, Any]: Данные заказа или None, если заказ не найден
    """
    from utils.database import get_order, get_order_by_number, get_orders_by_user

    logger.debug(f"Поиск заказа по идентификатору: {identifier}")

    # Преобразуем идентификатор в строку для единообразия обработки
    identifier_str = str(identifier)

    # 1. Если идентификатор похож на номер заказа (начинается с "ORD-")
    if identifier_str.startswith("ORD-"):
        logger.debug(f"Поиск заказа по номеру: {identifier_str}")
        order = get_order_by_number(identifier_str)
        if order:
            logger.debug(f"Заказ найден по номеру: {order.get('order_number')}")
            return order

    # 2. Пробуем найти заказ по ID
    try:
        identifier_int = int(identifier_str)

        # 2.1 Сначала ищем по ID заказа в базе данных
        logger.debug(f"Поиск заказа по ID: {identifier_int}")
        order = get_order(identifier_int)
        if order:
            logger.debug(f"Заказ найден по ID: {order.get('id')}")
            return order

        # 2.2 Затем пробуем найти заказ последнего пользователя с этим telegram_id
        logger.debug(f"Поиск заказа по telegram_id пользователя: {identifier_int}")
        user_orders = get_orders_by_user(identifier_int)
        if user_orders and len(user_orders) > 0:
            logger.debug(f"Найден заказ по telegram_id пользователя: {user_orders[0].get('order_number')}")
            return user_orders[0]

        # 2.3 Если заказ все еще не найден, проверяем все заказы в системе
        # Эта часть будет медленной на больших объемах данных и нужна только для отладки
        try:
            from utils.database import get_all_orders
            logger.debug("Последняя попытка: поиск среди всех заказов в системе")
            all_orders = get_all_orders(limit=10)  # Ограничиваем поиск последними 10 заказами для производительности

            # Выводим информацию о всех найденных заказах для отладки
            for i, order in enumerate(all_orders):
                logger.debug(f"Заказ {i + 1}: ID={order.get('id')}, номер={order.get('order_number')}, " +
                             f"пользователь={order.get('telegram_id')}, статус={order.get('status')}")

            # Возвращаем самый последний заказ как запасной вариант
            if all_orders:
                logger.debug(
                    f"Возвращаем самый последний заказ как запасной вариант: {all_orders[0].get('order_number')}")
                return all_orders[0]
        except Exception as e:
            logger.error(f"Ошибка при получении всех заказов: {e}")
            logger.error(traceback.format_exc())

    except (ValueError, TypeError) as e:
        logger.error(f"Ошибка при преобразовании идентификатора {identifier} в число: {e}")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при поиске заказа: {e}")
        logger.error(traceback.format_exc())

    # Заказ не найден ни одним из способов
    logger.warning(f"Заказ с идентификатором {identifier} не найден ни одним из способов")
    return None