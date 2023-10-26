import inspect
import os
import sys

import telegram.ext
from telegram.ext import ApplicationBuilder, Application

import bot
from logger import create_logger


def get_env_or_die(env_variable: str, *, exit_code: int = 1) -> str:
    logger = create_logger(inspect.currentframe().f_code.co_name)
    if token := os.getenv(env_variable):
        return token

    logger.critical(f"failed to retrieve token from environment (`{env_variable}`)")
    sys.exit(exit_code)


def main(application: Application):
    application.add_handler(telegram.ext.CommandHandler("cf", bot.cure))
    application.add_handler(telegram.ext.CommandHandler("cure_freedom", bot.cure))
    application.add_handler(telegram.ext.CommandHandler("supported_units", bot.supported_units))

    application.run_polling()


if __name__ == "__main__":
    bot_token = get_env_or_die("BOT_TOKEN", exit_code=1)
    _application = ApplicationBuilder().token(bot_token).build()

    main(_application)
