import psycopg2
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Параметры подключения к БД
DB_PARAMS = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "tg_bot"),
}


def update_tables():
    """Обновляет структуру таблиц"""
    connection = None
    cursor = None

    try:
        print("Подключение к базе данных...")
        connection = psycopg2.connect(**DB_PARAMS)
        cursor = connection.cursor()

        # Проверяем наличие столбца phone в таблице orders
        cursor.execute("""
                       SELECT column_name
                       FROM information_schema.columns
                       WHERE table_name = 'orders'
                         AND column_name = 'phone'
                       """)

        if not cursor.fetchone():
            print("Добавление столбца 'phone' в таблицу orders...")
            cursor.execute("""
                           ALTER TABLE orders
                               ADD COLUMN phone VARCHAR(20)
                           """)
        else:
            print("Столбец 'phone' уже существует в таблице orders")

        # Проверяем наличие столбца address в таблице orders
        cursor.execute("""
                       SELECT column_name
                       FROM information_schema.columns
                       WHERE table_name = 'orders'
                         AND column_name = 'address'
                       """)

        if not cursor.fetchone():
            print("Добавление столбца 'address' в таблицу orders...")
            cursor.execute("""
                           ALTER TABLE orders
                               ADD COLUMN address TEXT
                           """)
        else:
            print("Столбец 'address' уже существует в таблице orders")

        connection.commit()
        print("Обновление таблиц успешно завершено")

    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Ошибка при обновлении таблиц: {e}")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


if __name__ == "__main__":
    update_tables()