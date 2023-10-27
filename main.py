import aiohttp
from bs4 import BeautifulSoup
from logger import Logger
import dotenv
import os
import asyncio
import telebot
from telebot.async_telebot import AsyncTeleBot
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
import selenium.common.exceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

DEBUG = False
USING_PYCHARM_ENV = True

logger = Logger(
    debug=DEBUG,
    level=20  # logger.INFO
)
if not os.path.isfile('.env'):
    with open('.env', 'w') as f:
        f.write('TELEGRAM_BOT_API_TOKEN = ""\nOWNER_ID = ""\nLOGIN = ""\nPASSWORD = ""')
elif USING_PYCHARM_ENV or DEBUG:
    pass
else:
    dotenv.load_dotenv(f'{os.getcwd()}\\.env')

# bot = telebot.TeleBot(token=os.getenv('TELEGRAM_BOT_API_TOKEN'))
bot = AsyncTeleBot(token=os.getenv('TELEGRAM_BOT_API_TOKEN'))

async def get_table(cookies):
    async with aiohttp.ClientSession(cookies=cookies, headers={"User-Agent": user_agent}) as s:
        r = await s.get(url='https://cabinet.ruobr.ru/child/studies/mark_table/')
        r.raise_for_status()
        raw_html = await r.text(encoding='UTF-8')
        soup = BeautifulSoup(raw_html, 'lxml')
    raw_table = soup.find('table', {'id': 'in_rows', 'class': 'hide'})
    table = {}
    for row in raw_table.find('tbody').find_all('tr'):
        elements = []
        for element in row.find_all('td'):
            elements.append(element.string.strip().split('\n')[-1].strip(','))
        table[elements[0]] = elements[1].split(', ')
    # logger.info(table)
    return table


async def get_cookies():
    cookies = {}
    options = ChromeOptions()
    options.add_argument(f'--user-agent={user_agent}')  # Change useragent
    options.add_argument('--disable-blink-features=AutomationControlled')  # Disable webdriver detecting
    options.add_argument('--lang=en')  # Only English lang in browser
    options.add_argument("--log-level=OFF")  # Disable logs
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument('--headless')  # Run Browser without window
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1600, 900)
    driver.implicitly_wait(2)

    # Log in
    while True:
        try:
            driver.get(url='https://cabinet.ruobr.ru/login/')
            login_button = driver.find_element(By.ID, 'id_username')
            login_button.click()
            break
        except (selenium.common.exceptions.NoSuchElementException, ConnectionError) as ex:
            logger.error(ex)

    await asyncio.sleep(0.1)
    login = driver.find_element(By.ID, 'id_username')
    login.clear()
    login.send_keys(os.getenv('LOGIN'))

    await asyncio.sleep(0.1)
    password = driver.find_element(By.ID, 'id_password')
    password.clear()
    password.send_keys(os.getenv('PASSWORD'))
    password.send_keys(Keys.ENTER)
    await asyncio.sleep(1)

    for c in driver.get_cookies():
        cookies[c['name']] = c['value']
    driver.close()
    driver.quit()
    return cookies

@bot.message_handler(commands=['start'])
async def command_start_handler(message: telebot.types.Message) -> None:
    if message.chat.id == int(os.getenv('OWNER_ID')):
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        if DEBUG:
            keyboard.add(telebot.types.KeyboardButton(text="/id"), telebot.types.KeyboardButton(text="/start"))
        keyboard.add(telebot.types.KeyboardButton(text="/start_scrapper"), telebot.types.KeyboardButton(text="/get_tables"))
        await bot.reply_to(message, 'Готово', reply_markup=keyboard)
    elif os.getenv('OWNER_ID') == '':
        kb = [telebot.types.KeyboardButton(text="/id"),
              telebot.types.KeyboardButton(text="/start")]
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(*kb)
        await bot.reply_to(message, 'Укажите OWNER_ID в .env', reply_markup=keyboard)
    else:
        await bot.reply_to(message, 'Вы не владелец бота')

@bot.message_handler(commands=['start_scrapper'])
async def command_start_scrapper_handler(message: telebot.types.Message) -> None:
    if message.chat.id == int(os.getenv('OWNER_ID')):
        cookies = await get_cookies()
        old_table = {}
        while True:
            current_table = await get_table(cookies)
            if not old_table:
                logger.info('Первый запуск')
            elif not old_table == current_table:
                logger.info('Изменение')
                change = ''
                for i in current_table:
                    if current_table[i] != old_table[i]:
                        change += f'{i}: \nБыло: {old_table[i]}\nСтало: {current_table[i]}'
                await bot.send_message(os.getenv('OWNER_ID'), change)
            else:
                logger.info('Без изменений')
            old_table = current_table
            await asyncio.sleep(300)

@bot.message_handler(commands=['get_tables'])
async def command_start_scrapper_handler(message: telebot.types.Message) -> None:
    if message.chat.id == int(os.getenv('OWNER_ID')):
        cookies = await get_cookies()
        table = await get_table(cookies)
        ans = ''
        for name in table:
            only_marks = table[name]*1  # *1 нужно чтобы таблица и переменная не были связанны
            for i in range(only_marks.count('Н')):
                only_marks.remove('Н')
            for i in range(only_marks.count('УП')):
                only_marks.remove('УП')
            for i in range(only_marks.count('Б')):
                only_marks.remove('Б')
            only_marks = list(map(int, only_marks))
            ans += f'*{name}*: {", ".join(table[name])} - *{round(sum(only_marks) / len(only_marks), 2)}*\n'
        ans.strip('\n')
        logger.info(ans, to_console=False)
        await bot.reply_to(message, ans, parse_mode="Markdown")

@bot.message_handler(commands=['id'])
async def command_id_handler(message: telebot.types.Message) -> None:
    await bot.reply_to(message, f'Твой ID: {message.from_user.id}')


async def start():
    me = await bot.get_me()
    logger.info(f'Вход как {me.full_name}')
    await bot.infinity_polling()

if __name__ == '__main__':
    user_agent = UserAgent().firefox    # При смене юзер агента сайт выходит
    asyncio.run(start())
