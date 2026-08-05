#!/bin/bash

# ==========================================
# Скрипт автоматического бэкапа в Telegram
# ==========================================

# Настройки Telegram
BOT_TOKEN="8775953694:AAFTeZm2eEM4VzVQiryfH56OxBWcHUVuTf0"
CHAT_ID="-1004404372540"
# Раскомментируй строку ниже и вставь ID топика, если бэкапы не приходят или приходят не туда
# TOPIC_ID="id_топика_здесь"

# Переходим в папку проекта на сервере
cd /root/project/juventud || exit 1

# 1. Создаем дамп базы данных
echo "Создаем дамп базы данных..."
docker compose exec -T db sh -c 'pg_dump -U $POSTGRES_USER -d $POSTGRES_DB -c' > db_backup.sql

# 2. Упаковываем файлы в архив
DATE=$(date +%Y-%m-%d_%H-%M)
ARCHIVE_NAME="juventud_backup_${DATE}.tar.gz"

echo "Упаковываем файлы в архив $ARCHIVE_NAME..."
tar -czf "$ARCHIVE_NAME" db_backup.sql .env

# 3. Отправляем в Telegram
echo "Отправляем архив в Telegram..."

if [ -z "$TOPIC_ID" ]; then
    # Отправка в обычную группу
    curl -F chat_id="${CHAT_ID}" \
         -F document=@"${ARCHIVE_NAME}" \
         -F caption="📦 Backup ${DATE}" \
         "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument"
else
    # Отправка в конкретный топик супергруппы
    curl -F chat_id="${CHAT_ID}" \
         -F message_thread_id="${TOPIC_ID}" \
         -F document=@"${ARCHIVE_NAME}" \
         -F caption="📦 Backup ${DATE}" \
         "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument"
fi

# 4. Убираем за собой (удаляем архив и дамп с сервера)
echo "Удаляем временные файлы..."
rm db_backup.sql
rm "$ARCHIVE_NAME"

echo "Бэкап успешно завершен!"
