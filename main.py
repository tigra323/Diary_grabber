import requests
from bs4 import BeautifulSoup
from time import strftime as time
from logger import Logger
import dotenv
import os
import telebot

logger = Logger(
    debug=True,
    level=20  # logger.INFO
)
# dotenv.load_dotenv(f'{os.getcwd()}\\.env')
bot = telebot.TeleBot(token=os.getenv('TELEGRAM_BOT_API_TOKEN'))

@bot.message_handler(commands=['start'])
def command_start_handler(message: telebot.types.Message) -> None:
    if str(message.from_user.id) == os.getenv('OWNER_ID'):
        kb = [telebot.types.KeyboardButton(text="/id"),
              telebot.types.KeyboardButton(text="/start")]
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(*kb)
        keyboard.add(telebot.types.KeyboardButton(text="/start_scrapper"))
        bot.reply_to(message, 'Готово', reply_markup=keyboard)
    elif os.getenv('OWNER_ID') == '':
        kb = [telebot.types.KeyboardButton(text="/id"),
              telebot.types.KeyboardButton(text="/start")]
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(*kb)
        bot.reply_to(message, 'Укажите OWNER_ID в .env', reply_markup=keyboard)
    else:
        bot.reply_to(message, 'Вы не владелец бота')

@bot.message_handler(commands=['start_scrapper'])
def command_start_scrapper_handler(message: telebot.types.Message) -> None:
    pass    # TODO GRABBER AND BD

@bot.message_handler(commands=['id'])
def command_id_handler(message: telebot.types.Message) -> None:
    bot.reply_to(message, f'Твой ID: {message.from_user.id}')


if __name__ == '__main__':
    logger.info(f'Вход как {bot.get_me().full_name}')
    bot.infinity_polling()