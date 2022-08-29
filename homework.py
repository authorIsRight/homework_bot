import logging
import os
from pprint import pprint
import sys
import time

from http import HTTPStatus
from dotenv import load_dotenv 

import requests
import telegram
from telegram import ReplyKeyboardMarkup, Bot
from telegram.ext import CommandHandler, Updater

load_dotenv()

#убрать токены перед гит пуш в .env

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

print(PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)

RETRY_TIME = 60
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

# handlers allow to overcome problem with utf-8 
logging.basicConfig(handlers=[logging.FileHandler(
    'homewrok_bot.log',
    'a+',
    'utf-8'
    )],
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler(sys.stdout)
)

def send_message(bot, message):
    try:
        bot.send_message(
            chat_id = TELEGRAM_CHAT_ID,
            text = message)
        logger.info(f'Сообщение отправленно: {message}')    
    except telegram.TelegramError as e:
        logger.error(f'Сообщение НЕ отправленно: {message}. {e}')

def get_api_answer(current_timestamp):
    """Запрашивает инфу по домашкам у API яндекса
    в случае, если доступно, передает это на обработку
    в другие функции"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    # удалить после тестирования строку ниже
    params = {'from_date': 1659168456}
    try: 
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except homework_statuses.status_code != HTTPStatus.OK:
        logger.error(f'Проблема с доступом. Код: {homework_statuses.status_code}')               
    except requests.exceptions.RequestException as e:
        logger.error(f'Возникла ошибка, связанная с endpoint: {e}')       
    return homework_statuses.json()


def check_response(response):
    """Проверяет на то, что ответ API
    соответствует ожиданиям и возвращает 
    последнюю домащнюю работу"""
    if 'homeworks' not in response:
        logger.error('Unexpected return from API: key \'homeworks\' not found')
    if not isinstance(response, dict):
        logger.error('API did not return dictionary')
    if not isinstance(response['homeworks'], list):
        logger.error('API did not return list on homeworks')
    if not isinstance(response['homeworks'][0], dict):
        logger.error('API did not return dictionary on the last homework')
    if len(response) == 0:
        return {}
    return response['homeworks'][0]


def parse_status(homework):
    homework_name = homework['homework_name'] #pfvtybnm
    homework_status = homework['status']

    ...

    verdict = HOMEWORK_STATUSES[homework_status] #pfvtybnm

    ...

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем, что токены подключены"""
    empty_token_message = 'Работа программы требует наличия токенов'
    token_ok = True  
    tokens = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    for token in tokens:
        if token is None:
            token_ok = False
            logger.critical(f' {empty_token_message}')
    return token_ok      



def main():
    """Основная логика работы бота."""
    if not check_tokens(): 
        exit()        

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    #допилить
#    response = get_api_answer(current_timestamp) #подкорректировать
#    homework = check_response(response)    
    initial_status = ''

    while True:
        try:
            response = get_api_answer(current_timestamp) #подкорректировать
            homework = check_response(response)
            message = parse_status(homework)
            if homework['status'] != initial_status:
                send_message(bot, message)
                initial_status = homework['status']
            ...

            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            ...
            time.sleep(RETRY_TIME)
        else:
            ...


if __name__ == '__main__':
    main()
