from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery

from app.bot.handlers.private.windows import Window, online_sources_markup
from app.bot.manager import Manager
from app.bot.utils.redis import RedisStorage
from app.bot.utils.redis.models import UserData
from app.bot.utils.texts import SUPPORTED_LANGUAGES

router = Router()
router.callback_query.filter(F.message.chat.type == "private", StateFilter(None))


@router.callback_query()
async def handler(call: CallbackQuery, manager: Manager, redis: RedisStorage, user_data: UserData) -> None:
    """
    Handles callback queries for selecting the language and source.

    If the callback data is 'ru' or 'en', updates the user's language code in Redis and sets
    the language for the manager's text messages. Then, displays the main menu window.

    :param call: CallbackQuery object.
    :param manager: Manager object.
    :param redis: RedisStorage object.
    :param user_data: UserData object.
    :return: None
    """
    # Language selection
    if call.data in SUPPORTED_LANGUAGES.keys():
        user_data.language_code = call.data
        manager.text_message.language_code = call.data
        await redis.update_user(user_data.id, user_data)
        await manager.state.update_data(language_code=call.data)
        await Window.main_menu(manager)
        await call.answer()
        return
    
    # Source type selection (Online/Offline)
    if call.data == "source_online":
        # Show online sources menu
        reply_markup = online_sources_markup()
        await call.message.edit_reply_markup(reply_markup=reply_markup)
        await call.answer()
        return
    
    if call.data == "source_offline":
        # User selected offline source
        thanks_text = manager.text_message.get("thanks_feedback")
        await call.message.edit_text(thanks_text)
        await call.answer()
        return
    
    # Online source selection
    online_sources = [
        "source_telegram",
        "source_instagram", 
        "source_facebook",
        "source_google",
        "source_blogger"
    ]
    
    if call.data in online_sources:
        # User selected a specific online source
        thanks_text = manager.text_message.get("thanks_feedback")
        await call.message.edit_text(thanks_text)
        await call.answer()
        return

    await call.answer()
