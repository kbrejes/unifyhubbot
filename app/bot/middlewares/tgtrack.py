from typing import Callable, Dict, Any, Awaitable
import logging

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from app.bot.utils.tgtrack import TGTrackAPI
from app.config import Config

logger = logging.getLogger(__name__)


class TGTrackMiddleware(BaseMiddleware):
    """
    Middleware для интеграции с TGTrack API (Откуда Подписки).
    
    Перехватывает Update объекты, конвертирует их в формат webhook
    и отправляет в TGTrack API для отслеживания источников трафика.
    """

    def __init__(self, config: Config) -> None:
        """
        Инициализация middleware.

        :param config: Конфигурация приложения.
        """
        self.config = config
        self.tgtrack_api = None
        if config.tgtrack and config.tgtrack.ENABLED:
            self.tgtrack_api = TGTrackAPI(config.tgtrack)
            logger.info("TGTrack middleware initialized")

    def _convert_to_webhook_format(self, update_dict: dict) -> dict:
        """
        Конвертирует Update из формата aiogram в формат webhook от Telegram.
        
        Основная проблема: aiogram использует 'from_user', а Telegram API использует 'from'.
        
        :param update_dict: Словарь с данными Update от aiogram.
        :return: Словарь в формате webhook от Telegram.
        """
        # Рекурсивная функция для замены from_user -> from
        def convert_dict(obj):
            if isinstance(obj, dict):
                new_dict = {}
                for key, value in obj.items():
                    # Заменяем from_user на from
                    if key == "from_user":
                        new_dict["from"] = convert_dict(value)
                    else:
                        new_dict[key] = convert_dict(value)
                return new_dict
            elif isinstance(obj, list):
                return [convert_dict(item) for item in obj]
            else:
                return obj
        
        return convert_dict(update_dict)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        """
        Обработка Update.

        :param handler: Следующий обработчик.
        :param event: Update объект от Telegram.
        :param data: Дополнительные данные.
        :return: Результат выполнения handler.
        """
        # Если TGTrack не настроен, пропускаем
        if not self.tgtrack_api:
            return await handler(event, data)

        # Проверяем, является ли событие важным для TGTrack
        should_send = self._should_send_to_tgtrack(event)

        if should_send:
            # Конвертируем Update в dict (как в webhook от Telegram)
            try:
                update_dict = event.model_dump(mode='json', exclude_none=True)
                
                # Конвертируем в формат webhook (from_user -> from)
                webhook_dict = self._convert_to_webhook_format(update_dict)
                
                # Асинхронно отправляем в TGTrack (не блокируем основной поток)
                # Используем fire-and-forget подход
                import asyncio
                asyncio.create_task(
                    self.tgtrack_api.on_telegram_webhook(webhook_dict)
                )
            except Exception as e:
                logger.error(f"TGTrack middleware error: {e}", exc_info=True)

        # Продолжаем обработку независимо от результата TGTrack
        return await handler(event, data)

    def _should_send_to_tgtrack(self, update: Update) -> bool:
        """
        Определяет, нужно ли отправлять update в TGTrack.

        :param update: Update объект.
        :return: True если нужно отправить.
        """
        # Отправляем:
        # 1. Команды /start (старт бота)
        if update.message and update.message.text:
            if update.message.text.startswith("/start"):
                return True

        # 2. my_chat_member (блокировка/разблокировка бота)
        if update.my_chat_member:
            return True

        # Для остальных событий не отправляем
        return False

