# Аудит безопасности — Juventud

> Дата: 2026-07-18  
> Scope: весь проект (Django, Nginx, Docker, зависимости)

---

## Сводка

| Критичность | Кол-во |
|---|---|
| 🔴 Критическая | 2 |
| 🟠 Высокая | 4 |
| 🟡 Средняя | 5 |
| 🔵 Низкая | 3 |
| **Итого** | **14** |

---

## 🔴 Критические

### [C-1] `.env` содержит реальные секреты — риск утечки в git

**Файл:** `.env`, строки 2, 15, 22–23

```
SECRET_KEY=django-insecure-key-placeholder   ← placeholder, но...
EMAIL_HOST_PASSWORD=mssp.QDOj6Vs...          ← РЕАЛЬНЫЙ пароль MailerSend
NOWPAYMENTS_API_KEY=CTKYEY7-...              ← РЕАЛЬНЫЙ ключ NowPayments
NOWPAYMENTS_IPN_SECRET=hCQ3cH...             ← РЕАЛЬНЫЙ IPN-секрет
```

**Воздействие:** Если `.env` попадёт в git (случайный `git add .`) — все ключи
скомпрометированы навсегда (история git не удаляется). Злоумышленник может
инициировать платежи от имени магазина, подделать IPN-уведомления,
рассылать письма от вашего домена. `SECRET_KEY` с пометкой `insecure` означает,
что сессии и CSRF-токены могут быть подделаны.

**Фикс:**
1. `git log --all --oneline -- .env` — проверить что файл не в истории
2. Сгенерировать новый SECRET_KEY:
   `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
3. Ротировать NowPayments API key и IPN secret в личном кабинете
4. Ротировать пароль MailerSend
5. Добавить `.env.example` с пустыми значениями для документации

---

### [C-2] `/payments/process/` не проверяет владельца заказа — IDOR-уязвимость

**Файл:** `apps/payments/views.py:42` + `apps/orders/views.py:56`

```python
order_id = request.session.get('order_id')   # integer: 1, 2, 3...
order = get_object_or_404(Order, id=order_id)
```

**Воздействие:** `order_id` — инкрементный integer. Злоумышленник оформляет
свой заказ, получает `order_id=50`, затем вручную устанавливает в сессии
`order_id=1..49` и инициирует оплату **за чужой заказ** через payment provider.

**Фикс:**
```python
# apps/orders/models.py — добавить поле
import uuid
session_key = models.CharField(max_length=40, blank=True, default='')

# apps/orders/views.py — привязать заказ к сессии
order.session_key = request.session.session_key
order.save(update_fields=['session_key'])

# apps/payments/views.py — проверять владельца
order_id = request.session.get('order_id')
order = get_object_or_404(Order, id=order_id, session_key=request.session.session_key)
```

---

## 🟠 Высокие

### [H-1] Отсутствуют критические HTTP security headers

**Файл:** `config/settings.py`

| Заголовок | Статус | Риск |
|---|---|---|
| `SECURE_HSTS_SECONDS` | ❌ не задан | SSL-stripping, downgrade-атаки |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | ❌ не задан | — |
| `SECURE_CONTENT_TYPE_NOSNIFF` | ❌ не задан | MIME-sniffing атаки |
| `SECURE_REFERRER_POLICY` | ❌ не задан | Утечка URL в Referer-заголовке |
| `X_FRAME_OPTIONS` | не явно задан | Clickjacking (Django default: DENY — OK) |

**Фикс** — добавить в `settings.py` в блок `if not DEBUG:`:
```python
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'
```

---

### [H-2] Нет rate limiting — возможен DoS и спам

**Файлы:** `apps/cart/views.py`, `apps/orders/views.py`, `apps/payments/views.py`

Ни на одном endpoint нет ограничения частоты запросов:
- `POST /orders/create/` — можно создавать тысячи заказов (спам в БД + email-лимит MailerSend)
- `POST /payments/process/` — можно инициировать тысячи запросов к NowPayments API
- `POST /cart/add/<id>/` — можно бесконечно добавлять товары

**Фикс:**
```bash
pip install django-ratelimit
```
```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', block=True)
def order_create(request): ...

@ratelimit(key='ip', rate='3/m', block=True)
def payment_process(request): ...

@ratelimit(key='ip', rate='30/m', block=True)
def cart_add(request, product_id): ...
```

---

### [H-3] Небезопасный `int()` cast без обработки ошибок — HTTP 500

**Файл:** `apps/cart/views.py`, строки 12 и 33

```python
quantity = int(request.POST.get('quantity', 1))  # ValueError при 'abc', '!', None
```

**Воздействие:** Запрос с `quantity=abc` вызывает необработанный `ValueError` →
HTTP 500. При `DEBUG=True` — полная трассировка стека с путями и переменными.
Может засорять error-мониторинг.

**Фикс:**
```python
try:
    quantity = max(1, int(request.POST.get('quantity', 1)))
except (ValueError, TypeError):
    return HttpResponseBadRequest('Invalid quantity')
```

---

### [H-4] `DEBUG=True` в `.env` — риск случайного деплоя в debug-режиме

**Файл:** `.env`, строка 1

```
DEBUG=True
```

Если этот файл попадёт на production-сервер без изменений, Django будет
запущен в debug-режиме: все исключения с полным стеком, SQL-запросами и
переменными окружения видны в браузере. `django-debug-toolbar` становится
публично доступным.

**Фикс:** Иметь два отдельных файла:
- `.env` (локальный) — `DEBUG=True`
- `.env.production` (на сервере) — `DEBUG=False`

В `docker-compose.yml` явно указывать `env_file: - .env.production`,
а `.env` использовать только локально.

---

## 🟡 Средние

### [M-1] `|linebreaks` рендерит HTML из описания товара без экранирования — Stored XSS

**Файл:** `apps/catalog/templates/catalog/partials/product_detail_content.html:85`

```html
{{ product.description|linebreaks }}
```

**Воздействие:** Фильтр `linebreaks` оборачивает текст в `<p>` теги, но
**не экранирует HTML внутри**. Если в описании товара через Admin написать
`<script>document.cookie</script>` — скрипт выполнится у каждого покупателя.
Это Stored XSS — одна из наиболее опасных уязвимостей.

**Фикс:**
```html
{{ product.description|linebreaksbr }}
```
`linebreaksbr` сначала экранирует HTML (`<` → `&lt;`), затем заменяет `\n` на `<br>`.

---

### [M-2] `print()` в коде вместо logger — утечка данных в stdout

**Файл:** `apps/payments/services.py` (deprecated), строки 60, 62

```python
print(f"NOWPayments API Error: {e}")
print(f"Response content: {response.content}")
```

**Воздействие:** `response.content` может содержать фрагменты API-ответов
с суммами и идентификаторами. В Docker stdout собирается агрегаторами логов —
эти данные могут утечь. Файл помечен deprecated, но до удаления — уязвимость существует.

**Фикс:** Удалить `services.py` — он уже заменён `providers/nowpayments.py`.

---

### [M-3] Session fixation — отсутствует `cycle_key()` после создания заказа

**Файл:** `apps/orders/views.py`, строка 56

```python
request.session['order_id'] = order.id
```

После оформления заказа сессия не ротируется. Если злоумышленник перехватил
сессионный cookie до оформления заказа (через XSS или сниффинг) — он сохранит
доступ к сессии с `order_id` и может отслеживать статус чужого заказа.

**Фикс:**
```python
request.session.cycle_key()  # ротировать ключ сессии
request.session['order_id'] = order.id
```

---

### [M-4] `SESSION_COOKIE_AGE` не задан — сессии живут 2 недели по умолчанию

**Файл:** `config/settings.py`

Django default — 1209600 секунд (2 недели). Корзина и `order_id` хранятся
в сессии без явного срока. Пользователь может вернуться через 10 дней и
обнаружить в сессии старый `order_id`.

**Фикс:**
```python
SESSION_COOKIE_AGE = 86400 * 3   # 3 дня — разумный компромисс для магазина
SESSION_SAVE_EVERY_REQUEST = True  # продлевать при активности
```

---

### [M-5] `client_max_body_size 100M` в Nginx — избыточно

**Файл:** `nginx.conf`, строка 25

Обычная форма заказа весит <10KB. 100MB открыты для загрузки больших тел
запросов через POST — ненужная нагрузка на сервер.

**Фикс:**
```nginx
client_max_body_size 2M;   # достаточно для форм
```

---

## 🔵 Низкие

### [L-1] Order ID enumeration — предсказуемые integer ID

**Файл:** `apps/orders/models.py`

По `order_id` можно определить объём продаж магазина. Не критично,
но является information disclosure.

**Фикс (опционально):**
```python
import uuid
public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
```

---

### [L-2] Django 5.0.1 — не последний патч-релиз

**Файл:** `requirements.txt:1`

```
Django==5.0.1
```

С момента выхода 5.0.1 были выпущены патчи безопасности в ветке 5.x.

**Фикс:**
```bash
pip install "Django>=5.2,<6.0"
```

---

### [L-3] Redis без пароля

**Файл:** `docker-compose.yml:24` + `.env:20`

Redis закрыт внутри Docker-сети (`expose`, не `ports`) — это нормально.
Но если конфиг изменится или будет ошибка — доступ без аутентификации.

**Фикс:**
```yaml
redis:
  command: redis-server --requirepass ${REDIS_PASSWORD}
```
```
REDIS_PASSWORD=your_strong_password
CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
```

---

## Приоритет исправлений

| # | ID | Что делать | Усилие |
|---|---|---|---|
| 1 | **C-1** | Ротировать все скомпрометированные ключи | 15 мин |
| 2 | **M-1** | `linebreaks` → `linebreaksbr` | 2 мин |
| 3 | **H-1** | Добавить HSTS и security headers | 10 мин |
| 4 | **H-3** | Валидировать `quantity` в cart views | 10 мин |
| 5 | **M-5** | `client_max_body_size 2M` в nginx | 2 мин |
| 6 | **M-3** | `cycle_key()` после создания заказа | 5 мин |
| 7 | **M-4** | Задать `SESSION_COOKIE_AGE` | 5 мин |
| 8 | **C-2** | Проверка session_key при оплате (IDOR) | 30 мин |
| 9 | **H-2** | Rate limiting на ключевых endpoints | 1 час |
| 10 | **H-4** | Отдельные env-файлы для dev и prod | 30 мин |
| 11 | **M-2** | Удалить `services.py` (deprecated) | 10 мин |
| 12 | **L-3** | Redis с паролем | 15 мин |
| 13 | **L-2** | Обновить Django до последнего патча | 30 мин |
| 14 | **L-1** | UUID для публичных ID заказов | 2 часа |
