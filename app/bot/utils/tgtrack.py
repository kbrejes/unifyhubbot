import logging
from typing import Optional

import aiohttp

from app.config import TGTrackConfig

logger = logging.getLogger(__name__)

BASE_URL = "https://bot-api.tgtrack.ru/v1"


class TGTrackAPI:
    """Класс для работы с API 'Откуда Подписки'."""

    def __init__(self, config: TGTrackConfig):
        """
        Инициализация API клиента.

        :param config: Конфигурация TGTrack.
        """
        self.config = config
        self.api_key = config.API_KEY
        self.base_url = f"{BASE_URL}/{self.api_key}"

    async def on_telegram_webhook(self, update_dict: dict) -> bool:
        """
        Отправляет исходный объект Update от Telegram в TGTrack API.
        Этот метод эмулирует Вариант 1 интеграции (webhook).

        :param update_dict: Словарь с данными Update от Telegram.
        :return: True если запрос успешен, False в противном случае.
        """
        if not self.config.ENABLED:
            return False

        url = f"{self.base_url}/on_telegram_webhook"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url=url,
                    json=update_dict,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        # Проверяем код ошибки в ответе
                        error_code = result.get("error", {}).get("code", -1)
                        if error_code == 0:
                            logger.debug(f"TGTrack API: on_telegram_webhook - успешно")
                            return True
                        else:
                            logger.warning(
                                f"TGTrack API: on_telegram_webhook - ошибка: {result.get('error')}"
                            )
                    else:
                        logger.warning(
                            f"TGTrack API: on_telegram_webhook - HTTP {response.status}"
                        )
                        # Логируем тело ответа для отладки
                        try:
                            error_text = await response.text()
                            logger.debug(f"Response body: {error_text}")
                        except Exception:
                            pass
        except aiohttp.ClientError as e:
            logger.error(f"TGTrack API: on_telegram_webhook - network error: {e}")
        except Exception as e:
            logger.error(
                f"TGTrack API: on_telegram_webhook - unexpected error: {e}",
                exc_info=True,
            )

        return False

    async def send_reach_goal(self, user_id: int, target: str) -> bool:
        """
        Отправляет событие достижения цели пользователем.

        :param user_id: ID пользователя.
        :param target: Идентификатор цели в рекламной системе.
        :return: True если запрос успешен.
        """
        if not self.config.ENABLED:
            return False

        url = f"{self.base_url}/send_reach_goal"
        data = {
            "user_id": str(user_id),
            "target": target,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url=url,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        error_code = result.get("error", {}).get("code", -1)
                        if error_code == 0:
                            logger.debug(
                                f"TGTrack API: send_reach_goal ({target}) - успешно"
                            )
                            return True
                        else:
                            logger.warning(
                                f"TGTrack API: send_reach_goal - ошибка: {result.get('error')}"
                            )
                    else:
                        logger.warning(
                            f"TGTrack API: send_reach_goal - HTTP {response.status}"
                        )
        except Exception as e:
            logger.error(
                f"TGTrack API: send_reach_goal - error: {e}", exc_info=True
            )

        return False

