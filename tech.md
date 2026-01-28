# Техническое задание: E-commerce сайт для продажи одежды

## 1. Общее описание проекта

E-commerce платформа для продажи одежды с современным SPA-подобным интерфейсом.

## 2. Технологический стек

### Backend

- **Framework:** Django (latest stable)
- **Database:** PostgreSQL
- **Web Server:** Nginx
- **Containerization:** Docker

### Frontend

- **CSS Framework:** Tailwind CSS
- **Interactivity:** HTMX (для SPA-подобного поведения)
- **JavaScript Framework:** Alpine.js
- **Language:** English

### Payment Integration

- **Payment Gateway:** NOWPayments

## 3. Функциональные требования

### 3.1 Каталог продукции

- Отображение списка товаров (одежда)
- Фильтрация по категориям
- Динамическая загрузка контента через HTMX

### 3.2 Детальная страница товара

- Полная информация о товаре
- Изображения товара
- Размеры, цвета, описание
- Кнопка добавления в корзину

### 3.3 Корзина товаров

- Модальное окно для отображения корзины
- Добавление/удаление товаров
- Изменение количества товаров
- Расчет общей стоимости
- Реализация через HTMX и Alpine.js

### 3.4 Оформление заказа

- Форма создания заказа
- Валидация данных покупателя
- Сохранение заказа в базе данных

### 3.5 Оплата

- Интеграция с NOWPayments
- Обработка платежей
- Подтверждение оплаты
- Обновление статуса заказа

## 4. Технические требования

### 4.1 Архитектура кода

- Соблюдение принципов ООП (инкапсуляция, наследование, полиморфизм)
- Принцип DRY (Don't Repeat Yourself)
- Использование маппинга где необходимо (DTO, serializers)
- Разделение логики на слои (models, views, services)

### 4.2 Безопасность

- CSRF protection
- SQL injection prevention
- XSS protection
- Безопасное хранение секретов (environment variables)
- Валидация всех пользовательских данных
- Secure headers configuration
- HTTPS configuration

### 4.3 Best Practices

- Clean code principles
- Proper error handling
- Logging
- Database query optimization
- Proper use of Django ORM
- RESTful API design (where applicable)
- Atomic transactions for critical operations

### 4.4 Frontend (SPA-подобное поведение)

- Все переходы и обновления контента через HTMX
- Минимальные полные перезагрузки страницы
- Плавные переходы и обновления UI
- Responsive design через Tailwind CSS

### 4.5 Deployment

- Docker containerization
- Docker Compose configuration
- Nginx as reverse proxy
- Static files serving
- Media files handling
- Production-ready settings

## 5. Дополнительные требования

### 5.1 Код

- Без комментариев в коде
- Язык интерфейса: английский
- Clean и читаемый код

### 5.2 Database

- PostgreSQL схема с оптимизацией запросов
- Proper indexing
- Database migrations

### 5.3 Testing (опционально, но рекомендуется)

- Unit tests для критичной логики
- Integration tests для API endpoints

## 6. Структура проекта (примерная)

```
project/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── manage.py
├── config/
│   ├── settings/
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── catalog/
│   ├── cart/
│   ├── orders/
│   └── payments/
├── static/
├── media/
├── templates/
└── nginx/
```

## 7. Этапы разработки (рекомендуемые)

1. Setup проекта (Docker, Django, PostgreSQL)
2. Модели данных (Products, Categories, Orders)
3. Каталог и фильтрация
4. Детальная страница товара
5. Корзина (модальное окно)
6. Система заказов
7. Интеграция NOWPayments
8. Frontend полировка (HTMX, Alpine.js, Tailwind)
9. Nginx configuration
10. Security hardening
11. Testing и deployment