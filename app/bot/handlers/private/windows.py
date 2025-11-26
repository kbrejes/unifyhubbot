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
MEDIA_DIR = Path(__file__).parent.parent.parent / "media"


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
        else:
            return "greeting_evening"
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
    async def main_menu(manager: Manager, **_) -> None:
        """
        Display the main menu window.

        :param manager: Manager object.
        :return: None
        """
        text = manager.text_message.get("main_menu")
        get_to_know_us = manager.text_message.get("get_to_know_us")
        with suppress(IndexError, KeyError):
            text = text.format(full_name=hbold(manager.user.full_name))
        await manager.send_message(text)
        await asyncio.sleep(3)
        
        # Send photo with text and source selection buttons
        photo_path = MEDIA_DIR / "Давайте познакомимся поближе.png"
        reply_markup = source_type_markup()
        
        if photo_path.exists():
            # Send photo with caption and buttons
            photo = FSInputFile(photo_path)
            message = await manager.bot.send_photo(
                chat_id=manager.user.id,
                photo=photo,
                caption=get_to_know_us,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            await manager.state.update_data(message_id=message.message_id)
        else:
            # Fallback to text message if photo not found
            await manager.send_message(get_to_know_us, reply_markup=reply_markup, delete_previous_message=False)
        
        # Schedule delayed messages using asyncio (not apscheduler to avoid pickle issues)
        asyncio.create_task(Window._schedule_delayed_messages(
            manager.bot, 
            manager.user.id, 
            manager.text_message.language_code
        ))
        
        await manager.state.set_state(None)
    
    @staticmethod
    async def _schedule_delayed_messages(bot, user_id: int, language_code: str) -> None:
        """
        Schedule delayed messages after source selection using asyncio.
        
        :param bot: Bot instance
        :param user_id: User ID
        :param language_code: User's language code
        :return: None
        """
        try:
            # Wait 35 seconds and send greeting
            await asyncio.sleep(35)
            await Window._send_greeting(bot, user_id, language_code)
            
            # Wait 8 more seconds and send follow-up (total 43 seconds)
            await asyncio.sleep(8)
            await Window._send_follow_up(bot, user_id, language_code)
        except Exception as e:
            # Log error but don't crash if user blocks bot or other issues
            import logging
            logging.error(f"Error sending delayed messages to user {user_id}: {e}")
    
    @staticmethod
    async def _send_greeting(bot, user_id: int, language_code: str) -> None:
        """
        Send time-based greeting message.
        
        :param bot: Bot instance
        :param user_id: User ID
        :param language_code: User's language code
        :return: None
        """
        from app.bot.utils.texts import TextMessage
        
        text_message = TextMessage(language_code)
        greeting_key = get_time_of_day_greeting()
        greeting_text = text_message.get(greeting_key)
        await bot.send_message(user_id, greeting_text)
    
    @staticmethod
    async def _send_follow_up(bot, user_id: int, language_code: str) -> None:
        """
        Send follow-up message about corporate training.
        
        :param bot: Bot instance
        :param user_id: User ID
        :param language_code: User's language code
        :return: None
        """
        from app.bot.utils.texts import TextMessage
        
        text_message = TextMessage(language_code)
        follow_up_text = text_message.get("ready_to_help")
        await bot.send_message(user_id, follow_up_text)

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
