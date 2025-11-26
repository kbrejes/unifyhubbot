# Руководство по развертыванию бота

## Webhook vs Polling

### Текущая реализация (Polling)
В данный момент бот использует **polling** (long polling) - метод, при котором бот постоянно опрашивает серверы Telegram на наличие новых сообщений.

**Преимущества polling:**
- ✅ Проще в настройке (не требует SSL сертификата)
- ✅ Не требует публичного IP или домена
- ✅ Работает из любой сети (даже за NAT)
- ✅ Отлично для разработки и небольших ботов

**Недостатки polling:**
- ❌ Немного выше задержка ответа
- ❌ Постоянное подключение к Telegram API
- ❌ Чуть больше нагрузка на сервер

### Рекомендация по переходу на Webhook

**Webhook** - это метод, при котором Telegram сам отправляет обновления на ваш сервер.

**Когда стоит переходить на webhook:**
1. ✅ Когда у вас есть публичный домен с SSL сертификатом
2. ✅ Когда бот становится популярным (>1000 пользователей)
3. ✅ Когда критична минимальная задержка ответа
4. ✅ Когда хотите оптимизировать нагрузку на сервер

**Преимущества webhook:**
- ✅ Мгновенная доставка обновлений
- ✅ Меньше нагрузки на сервер
- ✅ Более профессиональное решение для production

**Недостатки webhook:**
- ❌ Требует SSL сертификат (Let's Encrypt бесплатно)
- ❌ Требует публичный домен или IP
- ❌ Сложнее в настройке

### Как добавить webhook (опционально)

Если хотите добавить поддержку webhook, вот изменения в `app/__main__.py`:

```python
# Вместо polling
async def main() -> None:
    # ... существующий код ...
    
    # Для webhook добавьте:
    WEBHOOK_ENABLED = env.bool("WEBHOOK_ENABLED", default=False)
    
    if WEBHOOK_ENABLED:
        WEBHOOK_URL = env.str("WEBHOOK_URL")  # https://yourdomain.com/webhook
        WEBHOOK_PATH = env.str("WEBHOOK_PATH", default="/webhook")
        WEBAPP_HOST = env.str("WEBAPP_HOST", default="0.0.0.0")
        WEBAPP_PORT = env.int("WEBAPP_PORT", default=8080)
        
        from aiohttp import web
        
        app = web.Application()
        
        # Настройка webhook
        await bot.set_webhook(
            url=WEBHOOK_URL + WEBHOOK_PATH,
            drop_pending_updates=True
        )
        
        # Регистрация webhook handler
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        include_routers(dp)
        register_middlewares(dp, config=config, redis=storage.redis, apscheduler=apscheduler)
        
        # Webhook handler
        async def handle_webhook(request):
            update = await request.json()
            await dp.feed_update(bot, Update(**update))
            return web.Response()
        
        app.router.add_post(WEBHOOK_PATH, handle_webhook)
        
        # Запуск webhook сервера
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, WEBAPP_HOST, WEBAPP_PORT)
        await site.start()
        
        print(f"Webhook server started on {WEBAPP_HOST}:{WEBAPP_PORT}")
        print(f"Webhook URL: {WEBHOOK_URL}{WEBHOOK_PATH}")
        
        # Держим приложение запущенным
        await asyncio.Event().wait()
    else:
        # Polling (текущий метод)
        await bot.delete_webhook()
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
```

Добавьте в `.env`:
```
WEBHOOK_ENABLED=false
WEBHOOK_URL=https://yourdomain.com
WEBHOOK_PATH=/webhook
WEBAPP_HOST=0.0.0.0
WEBAPP_PORT=8080
```

### Для production с webhook также обновите `docker-compose.yml`:

```yaml
services:
  bot:
    build:
      context: .
    container_name: support-bot
    command: sh -c "cd /usr/src/app && python -m app"
    restart: always
    depends_on:
      - redis
    volumes:
      - .:/usr/src/app
    networks:
      - network
    ports:
      - "8080:8080"  # Добавить порты для webhook
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

## Публичное развертывание

### ✅ Да, текущая конфигурация готова к публичному развертыванию!

Ваш бот уже настроен для работы в production с помощью Docker и Redis.

### Что нужно для публичного запуска:

1. **Сервер с Docker** (VPS/VDS)
   - Ubuntu 20.04/22.04 или аналог
   - Минимум 1GB RAM
   - Docker и Docker Compose установлены

2. **Создайте `.env` файл** на сервере:
```bash
# Bot Configuration
BOT_TOKEN=your_bot_token_here
BOT_DEV_ID=your_telegram_id
BOT_GROUP_ID=your_group_id
BOT_EMOJI_ID=your_emoji_id

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# TGTrack (опционально)
TGTRACK_ENABLED=false
TGTRACK_API_KEY=your_api_key
```

3. **Запустите на сервере:**
```bash
# Клонируйте репозиторий
git clone your_repo_url
cd unifyhub_bot

# Создайте .env файл с вашими данными
nano .env

# Запустите через Docker Compose
docker compose up -d

# Проверьте логи
docker compose logs -f bot
```

4. **Автозапуск при перезагрузке сервера:**
   - Уже настроено через `restart: always` в docker-compose.yml ✅

5. **Мониторинг:**
```bash
# Проверить статус
docker compose ps

# Посмотреть логи
docker compose logs -f

# Перезапустить бота
docker compose restart bot

# Обновить код
git pull
docker compose down
docker compose up -d --build
```

### Безопасность для production:

1. **Файрвол** - откройте только нужные порты:
```bash
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP (если используете webhook)
sudo ufw allow 443   # HTTPS (если используете webhook)
sudo ufw enable
```

2. **Резервное копирование Redis:**
```bash
# Добавьте в crontab
0 2 * * * docker exec support-redis redis-cli BGSAVE
```

3. **Логирование** - уже настроено через `setup_logger()` ✅

### Рекомендации для production:

1. ✅ **Используйте polling** для начала (текущая настройка)
2. ⚠️ **Добавьте мониторинг** (например, Prometheus + Grafana)
3. ⚠️ **Настройте alerts** на падение бота
4. ⚠️ **Регулярно делайте бэкапы** Redis
5. 🔄 **Перейдите на webhook** когда получите SSL сертификат

### CI/CD (опционально):

Для автоматического деплоя при push в GitHub:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Server

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            cd /path/to/unifyhub_bot
            git pull
            docker compose down
            docker compose up -d --build
```

## Итог

### Для текущего этапа:
- ✅ **Оставайтесь на polling** - это проще и надежнее для старта
- ✅ **Текущая Docker конфигурация готова** к публичному развертыванию
- ✅ **Бот будет работать стабильно** с polling на любом VPS

### Когда расти:
- 🔄 **Переходите на webhook** когда:
  - Получите домен и SSL
  - Пользователей станет >1000
  - Нужна минимальная задержка

---

**Вывод:** Развертывайте как есть с polling! Это отличное решение для production. Webhook - опциональная оптимизация для будущего.

