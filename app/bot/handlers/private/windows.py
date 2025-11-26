from contextlib import suppress
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hbold
from aiogram.types import FSInputFile

from app.bot.manager import Manager

from aiogram.types import InlineKeyboardMarkup as Markup
from aiogram.types import InlineKeyboardButton as Button
import asyncio

from app.bot.utils.texts import SUPPORTED_LANGUAGES

# Path to media files
# windows.py is in app/bot/handlers/private/, so we need 4 parents to get to app/
MEDIA_DIR = Path(__file__).parent.parent.parent.parent / "media"

# Global dict to store active delayed message tasks
_active_tasks = {}


async def send_bot_message_to_group(bot, user_id: int, message_id: int, config, message_thread_id: int, redis=None):
    """
    Forward bot's message to the group topic.
    
    :param bot: Bot instance
    :param user_id: User ID
    :param message_id: Message ID to forward
    :param config: Config instance
    :param message_thread_id: Thread ID in the group
    :param redis: RedisStorage instance (optional, for updating thread_id if needed)
    """
    from aiogram.exceptions import TelegramBadRequest
    from app.bot.utils.create_forum_topic import create_forum_topic
    import logging
    
    try:
        if message_thread_id:
            await bot.forward_message(
                chat_id=config.bot.GROUP_ID,
                from_chat_id=user_id,
                message_id=message_id,
                message_thread_id=message_thread_id,
            )
    except TelegramBadRequest as e:
        if "message thread not found" in e.message and redis:
            # Topic was deleted, recreate it
            logging.info(f"Topic not found for user {user_id}, recreating...")
            
            user_data = await redis.get_user(user_id)
            if user_data:
                user_data.message_thread_id = await create_forum_topic(
                    bot,
                    config,
                    user_data.full_name,
                )
                await redis.update_user(user_data.id, user_data)
                
                # Try to forward again with new topic
                await bot.forward_message(
                    chat_id=config.bot.GROUP_ID,
                    from_chat_id=user_id,
                    message_id=message_id,
                    message_thread_id=user_data.message_thread_id,
                )
        else:
            logging.error(f"Error forwarding bot message to group: {e}")
    except Exception as e:
        logging.error(f"Error forwarding bot message to group: {e}")


def select_language_markup() -> Markup:
    """
    Generate an inline keyboard markup for selecting the language.

    :return: InlineKeyboardMarkup
    """

    builder = InlineKeyboardBuilder().row(
        *[
            Button(text=text, callback_data=callback_data)
            for callback_data, text in SUPPORTED_LANGUAGES.items()
        ], width=2
    )
    return builder.as_markup()


def source_type_markup() -> Markup:
    """
    Generate an inline keyboard markup for selecting source type (Online/Offline).

    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        Button(text="Онлайн", callback_data="source_online"),
        Button(text="Офлайн", callback_data="source_offline"),
        width=2
    )
    return builder.as_markup()


def online_sources_markup() -> Markup:
    """
    Generate an inline keyboard markup for selecting online sources.

    :return: InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        Button(text="Телеграм-каналы / реклама", callback_data="source_telegram"),
        width=1
    )
    builder.row(
        Button(text="Инстаграм (реклама или подписка)", callback_data="source_instagram"),
        width=1
    )
    builder.row(
        Button(text="Facebook реклама", callback_data="source_facebook"),
        width=1
    )
    builder.row(
        Button(text="Поиск Google", callback_data="source_google"),
        width=1
    )
    builder.row(
        Button(text="Увидел у блогера", callback_data="source_blogger"),
        width=1
    )
    return builder.as_markup()


def get_time_of_day_greeting(user_timezone: str = "Europe/Moscow") -> str:
    """
    Get greeting based on user's time of day.
    
    :param user_timezone: User's timezone (default: Europe/Moscow)
    :return: Greeting message key
    """
    try:
        tz = ZoneInfo(user_timezone)
        user_time = datetime.now(tz)
        hour = user_time.hour
        
        if 6 <= hour < 12:
            return "greeting_morning"
        elif 12 <= hour < 18:
            return "greeting_day"
        elif 18 <= hour < 23:
            return "greeting_evening"
        else:
            return "greeting_night"
    except Exception:
        # Default to day greeting if timezone fails
        return "greeting_day"


class Window:

    @staticmethod
    async def select_language(manager: Manager) -> None:
        """
        Display the window for selecting the language.

        :param manager: Manager object.
        :return: None
        """
        text = manager.text_message.get("select_language")
        with suppress(IndexError, KeyError):
            text = text.format(full_name=hbold(manager.user.full_name))
        reply_markup = select_language_markup()
        await manager.send_message(text, reply_markup=reply_markup)

    @staticmethod
    async def main_menu(manager: Manager, user_data=None, **_) -> None:
        """
        Display the main menu window.

        :param manager: Manager object.
        :param user_data: UserData object (optional).
        :return: None
        """
        import time
        
        # Prevent rapid consecutive calls (debounce 2 seconds)
        state_data = await manager.state.get_data()
        last_menu_time = state_data.get("last_menu_time", 0)
        current_time = time.time()
        
        if current_time - last_menu_time < 3:
            # Called too soon after previous call, skip
            import logging
            logging.info(f"Skipping main_menu for user {manager.user.id} - called too soon")
            return
        
        # Update last menu time
        await manager.state.update_data(last_menu_time=current_time)
        
        text = manager.text_message.get("main_menu")
        get_to_know_us = manager.text_message.get("get_to_know_us")
        
        # Format text with user data
        request_id = user_data.request_id if user_data else "0000000"
        with suppress(IndexError, KeyError):
            text = text.format(
                full_name=hbold(manager.user.full_name),
                request_id=request_id
            )
        
        # Send first message (automatically forwards to group)
        msg1 = await manager.send_message(text)
        
        await asyncio.sleep(3)
        
        # Send photo with text and source selection buttons
        photo_path = MEDIA_DIR / "Давайте познакомимся поближе.png"
        reply_markup = source_type_markup()
        
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Photo path: {photo_path}")
        logger.info(f"Photo exists: {photo_path.exists()}")
        
        if photo_path.exists():
            try:
                # Send photo with caption and buttons
                photo = FSInputFile(photo_path)
                logger.info(f"Sending photo to user {manager.user.id}")
                message = await manager.bot.send_photo(
                    chat_id=manager.user.id,
                    photo=photo,
                    caption=get_to_know_us,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
                await manager.state.update_data(message_id=message.message_id)
                logger.info(f"Photo sent successfully, message_id: {message.message_id}")
                
                # Forward photo message to group (using manager's method)
                await manager._forward_to_group(message.message_id)
            except Exception as e:
                logger.error(f"Error sending photo: {e}", exc_info=True)
                # Fallback to text message if photo sending fails (automatically forwards to group)
                await manager.send_message(get_to_know_us, reply_markup=reply_markup, delete_previous_message=False)
        else:
            logger.warning(f"Photo not found at {photo_path}, sending text only")
            # Fallback to text message if photo not found (automatically forwards to group)
            await manager.send_message(get_to_know_us, reply_markup=reply_markup, delete_previous_message=False)
        
        # Cancel previous delayed tasks if any
        global _active_tasks
        state_data = await manager.state.get_data()
        old_task_id = state_data.get("delayed_task_id")
        if old_task_id:
            # Try to cancel old task (stored in a global dict)
            old_task = _active_tasks.get(old_task_id)
            if old_task and not old_task.done():
                old_task.cancel()
                _active_tasks.pop(old_task_id, None)
        
        # Schedule delayed messages using asyncio (not apscheduler to avoid pickle issues)
        # Get redis from middleware data
        redis = manager.middleware_data.get("redis")
        
        task_id = f"{manager.user.id}_{asyncio.get_event_loop().time()}"
        task = asyncio.create_task(Window._schedule_delayed_messages(
            manager.bot, 
            manager.user.id, 
            manager.text_message.language_code,
            task_id,
            manager.config,
            redis
        ))
        
        # Store task in global dict and state
        _active_tasks[task_id] = task
        await manager.state.update_data(delayed_task_id=task_id)
        
        await manager.state.set_state(None)
    
    @staticmethod
    async def _schedule_delayed_messages(bot, user_id: int, language_code: str, task_id: str, config=None, redis=None) -> None:
        """
        Schedule delayed messages after source selection using asyncio.
        
        :param bot: Bot instance
        :param user_id: User ID
        :param language_code: User's language code
        :param task_id: Unique task ID for cancellation
        :param config: Config instance (optional)
        :param redis: RedisStorage instance (optional)
        :return: None
        """
        try:
            # Wait 35 seconds and send greeting
            await asyncio.sleep(35)
            await Window._send_greeting(bot, user_id, language_code, config, redis)
            
            # Wait 8 more seconds and send follow-up (total 43 seconds)
            await asyncio.sleep(8)
            await Window._send_follow_up(bot, user_id, language_code, config, redis)
        except asyncio.CancelledError:
            # Task was cancelled, clean up silently
            import logging
            logging.info(f"Delayed messages task cancelled for user {user_id}")
        except Exception as e:
            # Log error but don't crash if user blocks bot or other issues
            import logging
            logging.error(f"Error sending delayed messages to user {user_id}: {e}")
        finally:
            # Clean up task from global dict
            _active_tasks.pop(task_id, None)
    
    @staticmethod
    async def _send_greeting(bot, user_id: int, language_code: str, config=None, redis=None) -> None:
        """
        Send time-based greeting message and forward to group.
        
        :param bot: Bot instance
        :param user_id: User ID
        :param language_code: User's language code
        :param config: Config instance (optional)
        :param redis: RedisStorage instance (optional)
        :return: None
        """
        from app.bot.utils.texts import TextMessage
        
        text_message = TextMessage(language_code)
        greeting_key = get_time_of_day_greeting()
        greeting_text = text_message.get(greeting_key)
        message = await bot.send_message(user_id, greeting_text)
        
        # Forward to group if config and redis are provided
        if config and redis:
            from app.bot.utils.redis.models import UserData
            user_data = await redis.get_user(user_id)
            if user_data and user_data.message_thread_id:
                await send_bot_message_to_group(
                    bot, user_id, message.message_id, config, user_data.message_thread_id, redis
                )
    
    @staticmethod
    async def _send_follow_up(bot, user_id: int, language_code: str, config=None, redis=None) -> None:
        """
        Send follow-up message about corporate training and forward to group.
        
        :param bot: Bot instance
        :param user_id: User ID
        :param language_code: User's language code
        :param config: Config instance (optional)
        :param redis: RedisStorage instance (optional)
        :return: None
        """
        from app.bot.utils.texts import TextMessage
        
        text_message = TextMessage(language_code)
        follow_up_text = text_message.get("ready_to_help")
        message = await bot.send_message(user_id, follow_up_text)
        
        # Forward to group if config and redis are provided
        if config and redis:
            from app.bot.utils.redis.models import UserData
            user_data = await redis.get_user(user_id)
            if user_data and user_data.message_thread_id:
                await send_bot_message_to_group(
                    bot, user_id, message.message_id, config, user_data.message_thread_id, redis
                )

    @staticmethod
    async def change_language(manager: Manager) -> None:
        """
        Display the window for changing the language.

        :param manager: Manager object.
        :return: None
        """
        text = manager.text_message.get("change_language")
        reply_markup = select_language_markup()
        await manager.send_message(text, reply_markup=reply_markup)

    @staticmethod
    async def command_source(manager: Manager) -> None:
        """
        Display the window with information about the command source.

        :param manager: Manager object.
        :return: None
        """
        text = manager.text_message.get("command_source")
        await manager.send_message(text)
