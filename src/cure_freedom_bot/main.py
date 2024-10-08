import inspect
import os
import sys

import telegram.ext
from telegram.ext import Application, ApplicationBuilder
from telegram.ext.filters import UpdateType

from cure_freedom_bot import bot
from cure_freedom_bot.logger import create_logger


def get_env_or_die(env_variable: str, *, exit_code: int = 1) -> str:
    frame = inspect.currentframe()
    if frame is None:
        logger = create_logger(__name__)
    else:
        logger = create_logger(frame.f_code.co_name)

    if token := os.getenv(env_variable):
        return token

    logger.critical("failed to retrieve token from environment (%s)", env_variable)
    sys.exit(exit_code)


def main(application: Application):
    application.add_handler(
        telegram.ext.CommandHandler("cf", bot.cure, filters=~UpdateType.EDITED_MESSAGE)
    )
    application.add_handler(
        telegram.ext.CommandHandler("cl", bot.cure, filters=~UpdateType.EDITED_MESSAGE)
    )
    application.add_handler(
        telegram.ext.CommandHandler(
            "cure_freedom", bot.cure, filters=~UpdateType.EDITED_MESSAGE
        )
    )
    application.add_handler(
        telegram.ext.CommandHandler(
            "cure_liberty", bot.cure, filters=~UpdateType.EDITED_MESSAGE
        )
    )
    application.add_handler(
        telegram.ext.CommandHandler("supported_units", bot.supported_units)
    )

    application.run_polling()


if __name__ == "__main__":
    bot_token = get_env_or_die("BOT_TOKEN", exit_code=1)
    _application = ApplicationBuilder().token(bot_token).build()

    main(_application)
