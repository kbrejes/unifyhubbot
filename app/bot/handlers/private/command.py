from aiogram import Router, F
from aiogram.filters import Command, MagicData
from aiogram.types import Message
from aiogram_newsletter.manager import ANManager

from app.bot.handlers.private.windows import Window
from app.bot.manager import Manager
from app.bot.utils.create_forum_topic import get_or_create_forum_topic
from app.bot.utils.redis import RedisStorage
from app.bot.utils.redis.models import UserData

router = Router()
router.message.filter(F.chat.type == "private")


@router.message(Command("start"))
async def handler(
        message: Message,
        manager: Manager,
        redis: RedisStorage,
        user_data: UserData,
) -> None:
    """
    Handles the /start command.

    Sets language to Russian by default and displays the main menu window.

    :param message: Message object.
    :param manager: Manager object.
    :param redis: RedisStorage object.
    :param user_data: UserData object.
    :return: None
    """
    # Set default language to Russian if not set
    if not user_data.language_code:
        user_data.language_code = "ru"
        manager.text_message.language_code = "ru"
    
    # Generate request ID if not exists
    if not user_data.request_id:
        user_data.request_id = await redis.get_next_request_id()
    
    # Save user data
    await redis.update_user(user_data.id, user_data)
    
    # Reset state to allow new flow (clear source_selected flag)
    await manager.state.update_data(
        language_code="ru", 
        request_id=user_data.request_id,
        source_selected=False
    )
    
    # Create the forum topic first
    await get_or_create_forum_topic(message.bot, redis, manager.config, user_data)
    
    # Delete user's /start command message
    await manager.delete_message(message)
    
    # Show main menu and forward bot messages to group
    await Window.main_menu(manager, user_data=user_data)


@router.message(Command("language"))
async def handler(message: Message, manager: Manager, user_data: UserData) -> None:
    """
    Handles the /language command.

    If the user has already selected a language, prompts the user to select a new language.
    Otherwise, prompts the user to select a language.

    :param message: Message object.
    :param manager: Manager object.
    :param user_data: UserData object.
    :return: None
    """
    if user_data.language_code:
        await Window.change_language(manager)
    else:
        await Window.select_language(manager)
    await manager.delete_message(message)


@router.message(Command("source"))
async def handler(message: Message, manager: Manager) -> None:
    """
    Handles the /source command.

    :param message: Message object.
    :param manager: Manager object.
    :return: None
    """
    text = manager.text_message.get("source")
    await manager.send_message(text)
    await manager.delete_message(message)


@router.message(
    Command("newsletter"),
    MagicData(F.event_from_user.id == F.config.bot.DEV_ID),  # type: ignore
)
async def handler(
        message: Message,
        manager: Manager,
        an_manager: ANManager,
        redis: RedisStorage,
) -> None:
    """
    Handles the /newsletter command.

    :param message: Message object.
    :param manager: Manager object.
    :param redis: RedisStorage object.
    :param an_manager: Manager object from aiogram_newsletter.
    :return: None
    """
    users_ids = await redis.get_all_users_ids()
    await an_manager.newsletter_menu(users_ids, Window.main_menu)
    await manager.delete_message(message)
