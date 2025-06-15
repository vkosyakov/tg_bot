import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import random
import string
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("database.log"),
        logging.StreamHandler()
    ]
)
# Определяем logger на уровне модуля - это было пропущено!
logger = logging.getLogger(__name__)


# Загрузка переменных окружения
load_dotenv()

# Параметры подключения к БД
DB_PARAMS = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "vlad1234"),
    "database": os.getenv("DB_NAME", "tg_bot"),
}


def get_connection():
    """Создает и возвращает соединение с БД"""
    return psycopg2.connect(**DB_PARAMS)


def generate_order_number():
    """Генерирует уникальный номер заказа"""
    timestamp = datetime.now().strftime("%y%m%d%H%M")
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ORD-{timestamp}-{random_chars}"


# Создание таблиц в базе данных
def create_tables():
    """Создает необходимые таблицы в базе данных"""
    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Таблица пользователей
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS users
                       (
                           id
                           SERIAL
                           PRIMARY
                           KEY,
                           telegram_id
                           BIGINT
                           UNIQUE
                           NOT
                           NULL,
                           username
                           VARCHAR
                       (
                           255
                       ),
                           first_name VARCHAR
                       (
                           255
                       ),
                           last_name VARCHAR
                       (
                           255
                       ),
                           phone VARCHAR
                       (
                           20
                       ),
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           )
                       """)

        # Таблица заказов
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS orders
                       (
                           id
                           SERIAL
                           PRIMARY
                           KEY,
                           order_number
                           VARCHAR
                       (
                           50
                       ) NOT NULL UNIQUE,
                           user_id INTEGER REFERENCES users
                       (
                           id
                       ),
                           amount DECIMAL
                       (
                           10,
                           2
                       ) NOT NULL,
                           delivery_cost DECIMAL
                       (
                           10,
                           2
                       ) DEFAULT 0,
                           discount DECIMAL
                       (
                           10,
                           2
                       ) DEFAULT 0,
                           items TEXT,
                           phone VARCHAR
                       (
                           20
                       ),
                           address TEXT,
                           status VARCHAR
                       (
                           20
                       ) NOT NULL DEFAULT 'created',
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           )
                       """)

        # Таблица платежей
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS payments
                       (
                           id
                           SERIAL
                           PRIMARY
                           KEY,
                           order_id
                           INTEGER
                           REFERENCES
                           orders
                       (
                           id
                       ) NOT NULL,
                           payment_id VARCHAR
                       (
                           100
                       ) UNIQUE,
                           amount DECIMAL
                       (
                           10,
                           2
                       ) NOT NULL,
                           payment_method VARCHAR
                       (
                           50
                       ),
                           status VARCHAR
                       (
                           20
                       ) NOT NULL DEFAULT 'pending',
                           payment_date TIMESTAMP,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           )
                       """)

        # Создание индексов для ускорения запросов
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id)")

        # Создание функции для автоматического обновления поля updated_at
        cursor.execute("""
                       CREATE
                       OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
                       BEGIN
               NEW.updated_at
                       = CURRENT_TIMESTAMP;
                       RETURN NEW;
                       END;
            $$
                       LANGUAGE 'plpgsql'
                       """)

        # Создание триггера для обновления updated_at
        cursor.execute("""
            DROP TRIGGER IF EXISTS update_orders_updated_at ON orders;
            CREATE TRIGGER update_orders_updated_at
            BEFORE UPDATE ON orders
            FOR EACH ROW
            EXECUTE PROCEDURE update_updated_at_column()
        """)

        connection.commit()
        print("Таблицы успешно созданы")

    except Exception as e:
        connection.rollback()
        print(f"Ошибка при создании таблиц: {e}")

    finally:
        cursor.close()
        connection.close()


# Сохранение пользователя
def save_user(user_data):
    """Сохраняет или обновляет пользователя в базе данных"""
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:
        telegram_id = user_data.get('id')
        username = user_data.get('username')
        first_name = user_data.get('first_name')
        last_name = user_data.get('last_name')
        phone = user_data.get('phone')

        # Проверяем, существует ли пользователь
        cursor.execute(
            "SELECT id FROM users WHERE telegram_id = %s",
            (telegram_id,)
        )
        user = cursor.fetchone()

        if user:
            # Обновляем существующего пользователя
            cursor.execute("""
                           UPDATE users
                           SET username   = %s,
                               first_name = %s,
                               last_name  = %s,
                               phone      = COALESCE(%s, phone)
                           WHERE telegram_id = %s RETURNING id
                           """, (username, first_name, last_name, phone, telegram_id))
        else:
            # Создаем нового пользователя
            cursor.execute("""
                           INSERT INTO users (telegram_id, username, first_name, last_name, phone)
                           VALUES (%s, %s, %s, %s, %s) RETURNING id
                           """, (telegram_id, username, first_name, last_name, phone))

        user_id = cursor.fetchone()['id']
        connection.commit()
        return user_id

    except Exception as e:
        connection.rollback()
        print(f"Ошибка при сохранении пользователя: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


# Получение пользователя по telegram_id
def get_user_by_telegram_id(telegram_id):
    """Получает пользователя по telegram_id"""
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute(
            "SELECT * FROM users WHERE telegram_id = %s",
            (telegram_id,)
        )
        user = cursor.fetchone()
        return user

    except Exception as e:
        print(f"Ошибка при получении пользователя: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


# Сохранение заказа
def save_order(user_id, order_data):
    """Создает новый заказ"""
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:
        amount = order_data.get('amount', 0)
        delivery_cost = order_data.get('delivery_cost', 0)
        discount = order_data.get('discount', 0)
        items = order_data.get('items', '')
        phone = order_data.get('phone', '')
        address = order_data.get('address', '')

        # Генерируем номер заказа
        order_number = generate_order_number()

        cursor.execute("""
                       INSERT INTO orders
                       (order_number, user_id, amount, delivery_cost, discount, items, phone, address, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id, order_number
                       """, (order_number, user_id, amount, delivery_cost, discount, items, phone, address, 'created'))

        order = cursor.fetchone()
        connection.commit()

        # Создаем полный объект заказа для возврата
        cursor.execute("""
                       SELECT o.*, u.telegram_id
                       FROM orders o
                                JOIN users u ON o.user_id = u.id
                       WHERE o.id = %s
                       """, (order['id'],))

        full_order = cursor.fetchone()
        return dict(full_order) if full_order else None

    except Exception as e:
        connection.rollback()
        print(f"Ошибка при создании заказа: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


# Получение заказа по ID или номеру
def get_order(order_id_or_number):
    """Получает заказ по ID, номеру заказа или telegram_id пользователя"""
    connection = None
    cursor = None

    try:
        logger.debug(f"Получение заказа по ID или номеру: {order_id_or_number}")

        connection = get_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)

        # Проверяем, является ли order_id_or_number числом (ID) или строкой (номер заказа)
        is_numeric = isinstance(order_id_or_number, int) or (
                    isinstance(order_id_or_number, str) and order_id_or_number.isdigit())

        if isinstance(order_id_or_number, str) and order_id_or_number.startswith('ORD-'):
            # Поиск по номеру заказа
            logger.debug(f"Поиск заказа по номеру: {order_id_or_number}")
            cursor.execute("""
                           SELECT o.*, u.telegram_id, u.first_name, u.last_name, u.username
                           FROM orders o
                                    JOIN users u ON o.user_id = u.id
                           WHERE o.order_number = %s
                           """, (order_id_or_number,))
        elif is_numeric:
            # Сначала пробуем найти по ID заказа
            logger.debug(f"Поиск заказа по ID: {order_id_or_number}")
            cursor.execute("""
                           SELECT o.*, u.telegram_id, u.first_name, u.last_name, u.username
                           FROM orders o
                                    JOIN users u ON o.user_id = u.id
                           WHERE o.id = %s
                           """, (order_id_or_number,))

            order = cursor.fetchone()

            # Если заказ не найден по ID, пробуем найти по telegram_id пользователя
            if not order:
                logger.debug(f"Заказ с ID {order_id_or_number} не найден, пробуем найти по telegram_id пользователя")
                cursor.execute("""
                               SELECT o.*, u.telegram_id, u.first_name, u.last_name, u.username
                               FROM orders o
                                        JOIN users u ON o.user_id = u.id
                               WHERE u.telegram_id = %s
                               ORDER BY o.created_at DESC LIMIT 1
                               """, (order_id_or_number,))
        else:
            # Пробуем найти по строковому представлению ID
            logger.debug(f"Поиск заказа по строковому ID: {order_id_or_number}")
            cursor.execute("""
                           SELECT o.*, u.telegram_id, u.first_name, u.last_name, u.username
                           FROM orders o
                                    JOIN users u ON o.user_id = u.id
                           WHERE o.id::text = %s
                           """, (order_id_or_number,))

        order = cursor.fetchone()

        if order:
            logger.debug(f"Заказ найден: {order}")
        else:
            logger.warning(f"Заказ с ID/номером {order_id_or_number} не найден")

        return dict(order) if order else None

    except Exception as e:
        logger.error(f"Ошибка при получении заказа: {e}")
        return None

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# Получение заказа по номеру
def get_order_by_number(order_number):
    """Получает заказ по номеру"""
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
                       SELECT o.*, u.telegram_id
                       FROM orders o
                                JOIN users u ON o.user_id = u.id
                       WHERE o.order_number = %s
                       """, (order_number,))

        order = cursor.fetchone()
        return dict(order) if order else None

    except Exception as e:
        print(f"Ошибка при получении заказа: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


# Получение всех заказов
def get_all_orders(limit=None, offset=0, status=None):
    """Получает все заказы с возможностью фильтрации по статусу"""
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:
        query = """
                SELECT o.*, u.telegram_id, u.first_name, u.last_name, u.username
                FROM orders o
                         JOIN users u ON o.user_id = u.id \
                """

        params = []

        if status:
            query += " WHERE o.status = %s"
            params.append(status)

        query += " ORDER BY o.created_at DESC"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        if offset:
            query += " OFFSET %s"
            params.append(offset)

        cursor.execute(query, params)
        orders = cursor.fetchall()

        return [dict(order) for order in orders] if orders else []

    except Exception as e:
        print(f"Ошибка при получении заказов: {e}")
        return []

    finally:
        cursor.close()
        connection.close()


# Получение заказов пользователя
def get_orders_by_user(telegram_id):
    """Получает все заказы пользователя"""
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
                       SELECT o.*, p.status as payment_status
                       FROM orders o
                                JOIN users u ON o.user_id = u.id
                                LEFT JOIN (SELECT order_id, status
                                           FROM payments
                                           WHERE status = 'succeeded'
                                              OR status = (SELECT status
                                                           FROM payments p2
                                                           WHERE p2.order_id = payments.order_id
                                                           ORDER BY created_at DESC
                                               LIMIT 1) ) p
                       ON p.order_id = o.id
                       WHERE u.telegram_id = %s
                       ORDER BY o.created_at DESC
                       """, (telegram_id,))

        orders = cursor.fetchall()
        return [dict(order) for order in orders] if orders else []

    except Exception as e:
        print(f"Ошибка при получении заказов пользователя: {e}")
        return []

    finally:
        cursor.close()
        connection.close()


# Обновление статуса заказа
def update_order_status(order_id, status):
    """Обновляет статус заказа"""
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
                       UPDATE orders
                       SET status = %s
                       WHERE id = %s RETURNING id, order_number, user_id
                       """, (status, order_id))

        order = cursor.fetchone()
        connection.commit()

        if not order:
            return None

        # Получаем telegram_id пользователя
        if order['user_id']:
            cursor.execute(
                "SELECT telegram_id FROM users WHERE id = %s",
                (order['user_id'],)
            )
            user = cursor.fetchone()
            if user:
                order['telegram_id'] = user['telegram_id']

        return dict(order)

    except Exception as e:
        connection.rollback()
        print(f"Ошибка при обновлении статуса заказа: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


# Обновление данных заказа
def update_order(order_id, order_data):
    """Обновляет данные заказа"""
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:
        # Формируем части SQL-запроса для обновления
        update_parts = []
        params = []

        # Проверяем, какие поля нужно обновить
        if 'phone' in order_data:
            update_parts.append("phone = %s")
            params.append(order_data['phone'])

        if 'address' in order_data:
            update_parts.append("address = %s")
            params.append(order_data['address'])

        if 'amount' in order_data:
            update_parts.append("amount = %s")
            params.append(order_data['amount'])

        if 'items' in order_data:
            update_parts.append("items = %s")
            params.append(order_data['items'])

        if 'status' in order_data:
            update_parts.append("status = %s")
            params.append(order_data['status'])

        if not update_parts:
            return None  # Нечего обновлять

        # Составляем и выполняем SQL-запрос
        query = f"""
            UPDATE orders 
            SET {', '.join(update_parts)}
            WHERE id = %s
            RETURNING id, order_number, user_id, status, phone, address, amount, items
        """

        params.append(order_id)
        cursor.execute(query, params)

        order = cursor.fetchone()
        connection.commit()

        return dict(order) if order else None

    except Exception as e:
        connection.rollback()
        print(f"Ошибка при обновлении заказа: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


# Сохранение платежа
def save_payment(payment_data):
    """Сохраняет информацию о платеже"""
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:
        order_id = payment_data.get('order_id')
        payment_id = payment_data.get('payment_id')
        amount = payment_data.get('amount')
        payment_method = payment_data.get('payment_method')
        status = payment_data.get('status', 'pending')

        # Проверяем, существует ли платеж
        cursor.execute(
            "SELECT id FROM payments WHERE payment_id = %s",
            (payment_id,)
        )
        payment = cursor.fetchone()

        if payment:
            # Обновляем существующий платеж
            cursor.execute("""
                           UPDATE payments
                           SET status       = %s,
                               payment_date = CASE WHEN %s = 'succeeded' THEN CURRENT_TIMESTAMP ELSE payment_date END
                           WHERE payment_id = %s RETURNING id
                           """, (status, status, payment_id))
        else:
            # Создаем новый платеж
            cursor.execute("""
                           INSERT INTO payments
                               (order_id, payment_id, amount, payment_method, status)
                           VALUES (%s, %s, %s, %s, %s) RETURNING id
                           """, (order_id, payment_id, amount, payment_method, status))

        payment_id_db = cursor.fetchone()['id']
        connection.commit()

        # Если платеж успешный, обновляем статус заказа
        if status == 'succeeded':
            update_order_status(order_id, 'paid')

        return payment_id_db

    except Exception as e:
        connection.rollback()
        print(f"Ошибка при сохранении платежа: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


# Получение платежа по ID
def get_payment_by_id(payment_id):
    """Получает платеж по ID"""
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
                       SELECT p.*, o.order_number, o.user_id, u.telegram_id
                       FROM payments p
                                JOIN orders o ON p.order_id = o.id
                                JOIN users u ON o.user_id = u.id
                       WHERE p.payment_id = %s
                       """, (payment_id,))

        payment = cursor.fetchone()
        return dict(payment) if payment else None

    except Exception as e:
        print(f"Ошибка при получении платежа: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


# Получение платежа по ID заказа
def get_payment_by_order_id(order_id):
    """Получает платеж по ID заказа"""
    connection = get_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
                       SELECT *
                       FROM payments
                       WHERE order_id = %s
                       ORDER BY created_at DESC LIMIT 1
                       """, (order_id,))

        payment = cursor.fetchone()
        return dict(payment) if payment else None

    except Exception as e:
        print(f"Ошибка при получении платежа: {e}")
        return None

    finally:
        cursor.close()
        connection.close()


# Получение всех платежей
def get_all_payments(limit=None, offset=0, status=None):
    """Получает все платежи с возможностью фильтрации по статусу"""
    connection = None
    cursor = None

    try:
        logger.debug(f"Получение всех платежей (limit: {limit}, offset: {offset}, status: {status})")

        connection = get_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)

        query = """
                SELECT p.*, o.order_number, u.telegram_id, u.first_name, u.last_name, u.username
                FROM payments p
                         JOIN orders o ON p.order_id = o.id
                         JOIN users u ON o.user_id = u.id \
                """

        params = []

        if status:
            query += " WHERE p.status = %s"
            params.append(status)

        query += " ORDER BY p.created_at DESC"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        if offset:
            query += " OFFSET %s"
            params.append(offset)

        cursor.execute(query, params)
        payments = cursor.fetchall()

        logger.debug(f"Найдено платежей: {len(payments) if payments else 0}")

        return [dict(payment) for payment in payments] if payments else []

    except Exception as e:
        logger.error(f"Ошибка при получении всех платежей: {e}")
        return []

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# Инициализация таблиц, если модуль запущен напрямую
if __name__ == "__main__":
    create_tables()


