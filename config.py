import logging

# This is a minimal configuration to get you started with the Text mode.
# If you want to connect Errbot to chat services, checkout
# the options in the more complete config-template.py from here:
# https://raw.githubusercontent.com/errbotio/errbot/master/errbot/config-template.py

BACKEND = "Telegram"
BOT_IDENTITY = {
    'token': '6233638283:AAFMy4nOun2OUnDkvX4wDehqfIyatCqpdEM',
}

BOT_DATA_DIR = r"/Users/k.pozhidaev/PycharmProjects/doggobot/data"
BOT_EXTRA_PLUGIN_DIR = r"/Users/k.pozhidaev/PycharmProjects/doggobot/plugins"

BOT_LOG_FILE = r"/Users/k.pozhidaev/PycharmProjects/doggobot/errbot.log"
BOT_LOG_LEVEL = logging.DEBUG

BOT_PREFIX = "/"
BOT_ALT_PREFIXES = ('Пес', 'Bot', 'Err')
BOT_ALT_PREFIXES_SEPARATORS = (':', ',', ':')

BOT_ADMINS = ('116755959',)  # Don't leave this as "@CHANGE_ME" if you connect your errbot to a chat system!!