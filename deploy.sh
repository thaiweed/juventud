#!/bin/bash
set -e

echo "🚀 Starting deploy..."

git pull origin main

echo "🔨 Rebuilding web container..."
docker-compose up -d --build web celery

echo "⏳ Waiting for web to start..."
sleep 5

echo "📦 Running migrations..."
docker-compose exec web python manage.py migrate

echo "📂 Collecting static files..."
docker-compose exec web python manage.py collectstatic --noinput

echo "✅ Deploy complete!"
