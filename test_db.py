import os
import sys
import random
from utils.database import (
    create_tables, save_user, get_user_by_telegram_id, save_order,
    get_order, get_order_by_number, get_orders_by_user, update_order_status
)


# Функция для генерации случайного телефонного номера
def generate_random_phone():
    return '+7' + ''.join([str(random.randint(0, 9)) for _ in range(10)])


def main():
    print("Запуск тестов для модуля database.py")

    # Шаг 1: Создание таблиц
    print("\n1. Создание таблиц...")
    try:
        create_tables()
        print("✅ Таблицы успешно созданы")
    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
        sys.exit(1)

    # Шаг 2: Создание тестового пользователя
    print("\n2. Создание тестового пользователя...")
    test_user_data = {
        'id': 123456789,  # тестовый telegram_id
        'username': 'test_user',
        'first_name': 'Test',
        'last_name': 'User',
        'phone': generate_random_phone()
    }

    try:
        user_id = save_user(test_user_data)
        if user_id:
            print(f"✅ Пользователь успешно сохранен, id: {user_id}")
        else:
            print("❌ Ошибка при сохранении пользователя")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка при сохранении пользователя: {e}")
        sys.exit(1)

    # Шаг 3: Получение пользователя
    print("\n3. Получение пользователя по telegram_id...")
    try:
        user = get_user_by_telegram_id(test_user_data['id'])
        if user:
            print(f"✅ Пользователь найден: {user}")
        else:
            print(f"❌ Пользователь с telegram_id {test_user_data['id']} не найден")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка при получении пользователя: {e}")
        sys.exit(1)

    # Шаг 4: Создание тестового заказа
    print("\n4. Создание тестового заказа...")
    test_order_data = {
        'amount': 1500.0,
        'items': 'Тестовый товар 1, Тестовый товар 2',
        'phone': test_user_data['phone'],
        'address': 'Тестовый адрес, дом 1, кв 1'
    }

    try:
        order = save_order(user_id, test_order_data)
        if order:
            print(f"✅ Заказ успешно создан: {order}")
            order_number = order['order_number']
        else:
            print("❌ Ошибка при создании заказа")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка при создании заказа: {e}")
        sys.exit(1)

    # Шаг 5: Получение заказа по номеру
    print(f"\n5. Получение заказа по номеру {order_number}...")
    try:
        retrieved_order = get_order_by_number(order_number)
        if retrieved_order:
            print(f"✅ Заказ найден: {retrieved_order}")
        else:
            print(f"❌ Заказ с номером {order_number} не найден")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка при получении заказа: {e}")
        sys.exit(1)

    # Шаг 6: Обновление статуса заказа
    print("\n6. Обновление статуса заказа...")
    try:
        updated_order = update_order_status(retrieved_order['id'], 'paid')
        if updated_order:
            print(f"✅ Статус заказа успешно обновлен: {updated_order}")
        else:
            print(f"❌ Не удалось обновить статус заказа")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка при обновлении статуса заказа: {e}")
        sys.exit(1)

    # Шаг 7: Получение всех заказов пользователя
    print("\n7. Получение всех заказов пользователя...")
    try:
        user_orders = get_orders_by_user(test_user_data['id'])
        if user_orders:
            print(f"✅ Найдено {len(user_orders)} заказов для пользователя")
            for i, order in enumerate(user_orders, 1):
                print(f"   Заказ {i}: {order['order_number']}, статус: {order['status']}")
        else:
            print(f"❌ Заказы для пользователя не найдены")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка при получении заказов пользователя: {e}")
        sys.exit(1)

    print("\n✅ Все тесты успешно пройдены!")


if __name__ == "__main__":
    main()