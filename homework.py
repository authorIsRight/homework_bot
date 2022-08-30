import logging
import os
import sys
import time
from dotenv import load_dotenv

import requests
import telegram


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

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
    'utf-8')],
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler(sys.stdout)
)


def send_message(bot, message):
    """Sends msg to Tg if status of HW changed."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message)
        logger.info(f'Сообщение отправленно: {message}')
    except telegram.TelegramError as e:
        logger.error(f'Сообщение НЕ отправленно: {message}. {e}')


def get_api_answer(current_timestamp):
    """Запрашивает инфу по домашкам у API яндекса.
    В случае, если доступно, передает это на обработку
    в другие функции.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    # uncommenting next row allows to get all homeworks
    # params = {'from_date': 1659168456}
    homework_statuses = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params=params
    )
    if homework_statuses.status_code != 200:
        raise requests.ConnectionError(homework_statuses.status_code)
    return homework_statuses.json()


def check_response(response):
    """Проверяет на то, что ответ API соответствует ожиданиям.
    возвращает последнюю домащнюю работу.
    """
    if len(response) == 0:
        raise KeyError("Empty dict")
    if 'homeworks' not in response:
        logger.error('Unexpected return from API: key \'homeworks\' not found')
    if not isinstance(response, dict):
        logger.error('API did not return dictionary')
    if not isinstance(response['homeworks'], list):
        logger.error('API did not return list on homeworks')
    if not isinstance(response['homeworks'][0], dict):
        logger.error('API did not return dictionary on the last homework')
    return response['homeworks'][0]


def parse_status(homework):
    """Извлекает из информации о конкретной домашке."""
    if len(homework) == 0:
        raise KeyError("Empty dict")
    if 'homework_name' not in homework:
        error_message = 'Ключ homework_name не найден в API'
        logger.error(error_message)
        raise KeyError(error_message)
    if 'status' not in homework:
        error_message = 'Ключ status не найден в API'
        logger.error(error_message)
        raise KeyError(error_message)
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        logger.error('Опять они что-то изменили в статусах домашек.'
                     'Опять все переделывать')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем, что токены подключены."""
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

    initial_status = ''
    error_message = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            if homework['status'] != initial_status:
                send_message(bot, message)
                initial_status = homework['status']

            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            new_error_message = str(error)
            if new_error_message != error_message:
                send_message(bot, message)
                error_message = new_error_message
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
