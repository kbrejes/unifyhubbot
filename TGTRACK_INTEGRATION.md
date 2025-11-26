# Интеграция с TGTrack (Откуда Подписки)

Этот бот интегрирован с сервисом [TGTrack (Откуда Подписки)](https://doc.tgtrack.ru/) для отслеживания источников трафика и передачи конверсий в рекламные системы (Яндекс.Директ, VK, Facebook/Instagram, Google Ads).

## Что было реализовано

Использован **Вариант 1** интеграции (`on_telegram_webhook`) с эмуляцией webhook через polling:
- Middleware перехватывает все Update объекты
- Конвертирует их в формат webhook от Telegram
- Отправляет в TGTrack API для отслеживания

## Настройка

### 1. Получите API ключ

1. Напишите боту [@otkudapodbotbot](https://t.me/otkudapodbotbot)
2. Следуйте инструкциям для получения API ключа
3. Документация: https://doc.tgtrack.ru/doc/custom-bot-api

### 2. Добавьте переменные в .env

Добавьте в ваш `.env` файл:

```env
# TGTrack API (Откуда Подписки)
TGTRACK_ENABLED=true
TGTRACK_API_KEY=ваш_api_ключ_здесь
```

### 3. Перезапустите бота

```bash
docker-compose restart
```

## Что отслеживается

### Автоматически отслеживаемые события:

1. **Старт бота** (`/start`) - передается в рекламные системы
   - Поддерживает параметры start (например: `/start TGTrack-PJ123456`)
   
2. **Блокировка бота** (my_chat_member) - для отслеживания отписок

### Проверка интеграции

После настройки проверьте работу на странице: https://bot-api.tgtrack.ru/last_events

1. Введите ваш API-ключ
2. Запустите бота от имени тестового пользователя с командой `/start`
3. Убедитесь, что событие появилось в списке со статусом `0` (успешно)

**Важно:** Middleware автоматически конвертирует формат aiogram (`from_user`) в формат Telegram webhook (`from`), поэтому события должны приниматься без ошибок 422.

## Глубокие цели (опционально)

Для отслеживания дополнительных целей (например, отправка первого сообщения, оставление номера телефона) используйте метод `send_reach_goal`:

```python
from app.bot.utils.tgtrack import TGTrackAPI
from app.config import Config

# В вашем обработчике
if config.tgtrack:
    tgtrack = TGTrackAPI(config.tgtrack)
    await tgtrack.send_reach_goal(
        user_id=user_data.id,
        target="user_sent_first_message",  # ваш идентификатор цели
    )
```

Примеры целей:
- `user_sent_first_message` - пользователь отправил первое сообщение
- `user_shared_phone` - пользователь поделился номером телефона
- `user_completed_survey` - пользователь прошел опрос
- И т.д. (настраивается в рекламных системах)

## Архитектура

### Файлы интеграции:

- `app/config.py` - добавлен `TGTrackConfig`
- `app/bot/utils/tgtrack.py` - API клиент для TGTrack
- `app/bot/middlewares/tgtrack.py` - middleware для автоматической отправки событий
- `app/bot/middlewares/__init__.py` - регистрация middleware

### Как это работает:

1. **TGTrackMiddleware** перехватывает все Update объекты
2. Проверяет, является ли событие важным (старт бота или блокировка)
3. Конвертирует Update в dict (формат webhook от Telegram)
4. Асинхронно отправляет в TGTrack API методом `on_telegram_webhook`
5. Не блокирует основной поток обработки

### Преимущества подхода:

- ✅ Минимум изменений в существующем коде
- ✅ Автоматическая отправка событий
- ✅ Не влияет на производительность (fire-and-forget)
- ✅ Легко отключить (TGTRACK_ENABLED=false)
- ✅ Полный контекст от Telegram передается в TGTrack

## Отключение интеграции

Чтобы отключить интеграцию, в `.env`:

```env
TGTRACK_ENABLED=false
```

Или просто удалите переменные `TGTRACK_*` из `.env`.

## Логирование

Логи TGTrack доступны в основном логе бота:

```bash
docker-compose logs -f
```

Ищите строки с префиксом `TGTrack API:`.

## Поддержка

- Документация TGTrack: https://doc.tgtrack.ru/
- Бот поддержки: [@otkudapodbotbot](https://t.me/otkudapodbotbot)
- Сообщество: [Telegram](https://t.me/otkudapodbot)

