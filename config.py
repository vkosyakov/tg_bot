import logging

logger = logging.getLogger(__name__)

# Telegram Bot Token - получите у @BotFather
BOT_TOKEN = "8140394776:AAFmKuU8tWhITdyV06Rz_jn8XjlKROgtwTg"
# ID группы администраторов
# Для получения ID группы:
# 1. Добавьте бота @getidsbot в вашу группу
# 2. Или отправьте сообщение из группы боту @userinfobot
# 3. Или используйте API-запрос getUpdates после добавления бота в группу
#
# ВАЖНО:
# - Группа должна быть публичной ИЛИ
# - Ваш бот должен быть администратором группы ИЛИ
# - ID группы обычно начинается с "-100"
ADMIN_GROUP_ID = "-4773126233"  # Замените на ID вашей группы
# Проверка корректности ID группы
if ADMIN_GROUP_ID == "REPLACE_WITH_YOUR_GROUP_ID":
    logger.warning("ADMIN_GROUP_ID не установлен. Заказы будут отправляться пользователю для демонстрации.")
elif not ADMIN_GROUP_ID.startswith("-"):
    logger.warning(f"ADMIN_GROUP_ID имеет неправильный формат: {ADMIN_GROUP_ID}. ID группы должен начинаться с '-'.")

# Conversation states - добавляем новые состояния для оплаты и статуса заказа
MENU, CART, CHECKOUT, PHONE, ADDRESS, CONFIRMATION, PAYMENT, ORDER_STATUS = range(8)

# Статусы заказа
ORDER_STATUSES = {
    "pending": "Ожидает подтверждения",
    "approved": "Подтвержден",
    "paid": "Оплачен",
    "preparing": "Готовится",
    "delivering": "В доставке",
    "completed": "Доставлен",
    "rejected": "Отклонен",
    "cancelled": "Отменен клиентом"
}
