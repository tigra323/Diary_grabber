import aiohttp
from bs4 import BeautifulSoup
from logger import Logger
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
# from icecream import ic

DEBUG = False
USING_PYCHARM_ENV = False

logger = Logger(
    debug=DEBUG,
    level=20  # logger.INFO
)
working_scrapper = False
working_cookie = False
cookies = {}
user_agent = UserAgent().firefox  # При смене юзер агента сайт выходит
if USING_PYCHARM_ENV or DEBUG:
    pass
elif not os.path.isfile('.env'):
    with open('.env', 'w') as f:
        f.write('TELEGRAM_BOT_API_TOKEN = ""\nOWNER_ID = ""\nLOGIN = ""\nPASSWORD = ""')
    import dotenv
    dotenv.load_dotenv(f'{os.getcwd()}\\.env')
else:
    import dotenv
    dotenv.load_dotenv(f'{os.getcwd()}\\.env')

if not os.getenv('TELEGRAM_BOT_API_TOKEN'):
    logger.critical('Впишите токен в .env')
    raise Exception

class ExceptionHandler(telebot.ExceptionHandler):
    def handle(self, exception):
        logger.error(exception)


bot = AsyncTeleBot(token=os.getenv('TELEGRAM_BOT_API_TOKEN'), exception_handler=ExceptionHandler())

@bot.callback_query_handler(func=lambda call: True)
async def handle_query(call):
    if call.data == 'back':
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text='Выберете предмет:', reply_markup=await subject_keyboard())
    else:
        await check_cookies()
        table = await get_table()
        only_marks_table = {}
        for name in table:
            only_marks = table[name]*1  # *1 нужно чтобы таблица и переменная не были связанны
            for i in range(only_marks.count('Н')):
                only_marks.remove('Н')
            for i in range(only_marks.count('УП')):
                only_marks.remove('УП')
            for i in range(only_marks.count('Б')):
                only_marks.remove('Б')
            if only_marks and only_marks != ['']:
                only_marks_table[name] = list(map(int, only_marks))*1
            else:
                only_marks_table[name] = []

        ans = f'{call.data}\n'
        ans += f'Текущие оценки: {table[call.data]}\n'
        if only_marks_table[call.data]:
            suma = sum(only_marks_table[call.data])
        else:
            suma = 0
        if len(only_marks_table[call.data]):
            length = len(only_marks_table[call.data])
        else:
            length = 1

        ans += f'Текущий средний балл: {round(suma / length, 2)}\n'
        ans += '\n'
        ans += f'При получении 5: {round((suma + 5) / (len(only_marks_table[call.data]) + 1), 2)}\n'
        ans += f'При получении 4: {round((suma + 4) / (len(only_marks_table[call.data]) + 1), 2)}\n'
        ans += f'При получении 3: {round((suma + 3) / (len(only_marks_table[call.data]) + 1), 2)}\n'
        ans += f'При получении 2: {round((suma + 2) / (len(only_marks_table[call.data]) + 1), 2)}\n'
        ans += f'При получении 1: {round((suma + 1) / (len(only_marks_table[call.data]) + 1), 2)}\n'

        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                    text=ans, reply_markup=await back_keyboard())

async def build_menu(buttons, n_cols,
                     header_buttons=None,
                     footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        menu.append([footer_buttons])
    return menu

async def subject_keyboard():
    await check_cookies()
    table = await get_table()
    inline_buttons_list = []
    for name in table.keys():
        if name in table:
            inline_buttons_list.append(telebot.types.InlineKeyboardButton(name, callback_data=name))
    return telebot.types.InlineKeyboardMarkup(await build_menu(inline_buttons_list, n_cols=2))

async def back_keyboard():
    return telebot.types.InlineKeyboardMarkup(
        keyboard=[[
                telebot.types.InlineKeyboardButton(
                    text='⬅',
                    callback_data='back'
                )]])

async def get_table() -> dict:
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
        table[elements[0]] = elements[1].split(', ')[::-1]
    return table

async def check_cookies() -> None:
    global cookies
    global working_cookie
    while working_cookie:
        await asyncio.sleep(1)
    if cookies:
        async with aiohttp.ClientSession(cookies=cookies, headers={"User-Agent": user_agent}) as s:
            r = await s.get(url='https://cabinet.ruobr.ru/child/studies/mark_table/')
            r.raise_for_status()
            raw_html = await r.text(encoding='UTF-8')
            soup = BeautifulSoup(raw_html, 'lxml')
            if soup.find('button', {'class': 'fluid ui primary button'}):
                logger.info('Куки устарели')
                cookies = await get_cookies()
    else:
        cookies = await get_cookies()

async def get_cookies() -> dict:
    global working_cookie
    logger.info('Получение куки')
    working_cookie = True
    await bot.send_message(os.getenv('OWNER_ID'), 'Получение куки')
    lcookies = {}
    options = ChromeOptions()
    options.add_argument(f'--user-agent={user_agent}')  # Change useragent
    options.add_argument('--disable-blink-features=AutomationControlled')  # Disable webdriver detecting
    options.add_argument('--lang=en')  # Only English lang in browser
    options.add_argument("--log-level=OFF")  # Disable logs
    options.add_argument('--allow-insecure-localhost')
    options.add_argument('--ignore-certificate-errors')
    options.accept_insecure_certs = True
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
        lcookies[c['name']] = c['value']
    driver.close()
    driver.quit()
    working_cookie = False
    return lcookies

@bot.message_handler(commands=['start'])
async def command_start_handler(message: telebot.types.Message) -> None:
    if str(message.chat.id) == os.getenv('OWNER_ID'):
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        if DEBUG:
            keyboard.add(telebot.types.KeyboardButton(text="/id"), telebot.types.KeyboardButton(text="/start"))
        keyboard.add(telebot.types.KeyboardButton(text="/start_scrapper"),
                     telebot.types.KeyboardButton(text="/get_tables"))
        keyboard.add(telebot.types.KeyboardButton(text="/more_info"))
        await bot.reply_to(message, 'Готово', reply_markup=keyboard)
    elif not os.getenv('OWNER_ID'):
        kb = [telebot.types.KeyboardButton(text="/id"),
              telebot.types.KeyboardButton(text="/start")]
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(*kb)
        await bot.reply_to(message, 'Укажите OWNER_ID в .env', reply_markup=keyboard)
    else:
        await bot.reply_to(message, 'Вы не владелец бота')

@bot.message_handler(commands=['start_scrapper'])
async def command_start_scrapper_handler(message: telebot.types.Message) -> None:
    if str(message.chat.id) == os.getenv('OWNER_ID'):
        global working_scrapper
        if not working_scrapper:
            working_scrapper = True
            old_table = {}
            current_table = {}
            while True:
                try:
                    await check_cookies()
                    current_table = await get_table()
                    # ic(current_table)
                    if not old_table:
                        logger.info('Первый запуск')
                        await bot.send_message(os.getenv('OWNER_ID'), 'Скраппер запущен')
                        if os.path.isfile('last.txt'):
                            with open('last.txt', 'r', encoding='utf8') as f:
                                for line in f:
                                    line = line.strip().split(':')
                                    old_table[line[0]] = line[-1].split(',')
                            logger.info('Загружена последняя таблица')
                            # logger.info(old_table)
                    elif not old_table == current_table:
                        logger.info('Изменение')
                        change = ''
                        logger.info(old_table, to_console=False)
                        logger.info(current_table, to_console=False)
                        for i in current_table:
                            if current_table[i] != old_table[i]:
                                new = []
                                removed = []
                                marks = (set(current_table[i]) | set(old_table[i])) - {''}
                                for mark in marks:
                                    if current_table[i].count(mark) - old_table[i].count(mark) > 0:
                                        for _ in range(current_table[i].count(mark) - old_table[i].count(mark)):
                                            new.append(mark)
                                    elif current_table[i].count(mark) - old_table[i].count(mark) < 0:
                                        for _ in range(old_table[i].count(mark) - current_table[i].count(mark)):
                                            removed.append(mark)
                                if (not new) and (not removed):
                                    logger.info(f'Без изменений, поменялся порядок у {i}')
                                    continue
                                logger.info(new, removed)
                                change += f'{i}:\n'
                                if new:
                                    logger.info(f'Добавили: {new}')
                                    change += f'Добавили: {new}\n'
                                if removed:
                                    logger.info(f'Убрали: {removed}')
                                    change += f'Убрали: {removed}\n'
                                logger.info(change, to_console=False)
                                change += '\n'
                                # change += f'{i}: \nБыло: {old_table[i]}\nСтало: {current_table[i]}\n\n'
                        if change:
                            await bot.send_message(os.getenv('OWNER_ID'), change.strip('\n'))
                        else:
                            logger.info('Ложное срабатывание')
                    else:
                        logger.info('Без изменений')
                    old_table = current_table
                    with open('last.txt', 'w', encoding='utf8') as f:
                        for line in current_table:
                            f.write(line + ':' + ','.join(current_table[line]) + '\n')
                except Exception as ex:
                    logger.critical(ex)
                    logger.error(str(old_table) + '\n' + str(current_table))
                    await bot.send_message(os.getenv('OWNER_ID'), str(ex) + '\n' + str(old_table) + '\n' + str(current_table))
                await asyncio.sleep(60 * 3)
        else:
            await bot.send_message(os.getenv('OWNER_ID'), 'Уже запущено')

@bot.message_handler(commands=['get_tables'])
async def command_start_scrapper_handler(message: telebot.types.Message) -> None:
    if str(message.chat.id) == os.getenv('OWNER_ID'):
        await check_cookies()
        table = await get_table()
        ans = ''
        for name in table:
            only_marks = table[name] * 1  # *1 нужно чтобы таблица и переменная не были связанны
            for i in range(only_marks.count('Н')):
                only_marks.remove('Н')
            for i in range(only_marks.count('УП')):
                only_marks.remove('УП')
            for i in range(only_marks.count('Б')):
                only_marks.remove('Б')

            if only_marks and only_marks != ['']:
                only_marks = list(map(int, only_marks))
            else:
                only_marks = []

            if only_marks:
                avg = round(sum(only_marks) / len(only_marks), 2)
            else:
                avg = 0

            ans += f'*{name}*: {", ".join(table[name])} - *{avg}*\n'
        logger.info(ans.strip('\n'), to_console=False)
        await bot.reply_to(message, ans.strip('\n'), parse_mode="Markdown")

@bot.message_handler(commands=['id'])
async def command_id_handler(message: telebot.types.Message) -> None:
    await bot.reply_to(message, f'Твой ID: {message.from_user.id}')

@bot.message_handler(commands=['more_info'])
async def command_id_handler(message: telebot.types.Message) -> None:
    if str(message.chat.id) == os.getenv('OWNER_ID'):
        await bot.reply_to(message, 'Выберете предмет', reply_markup=await subject_keyboard())

async def start() -> None:
    me = await bot.get_me()
    logger.info(f'Вход как {me.full_name}')
    await bot.infinity_polling(skip_pending=True)


if __name__ == '__main__':
    asyncio.run(start())
