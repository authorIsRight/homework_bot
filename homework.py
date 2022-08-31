import logging
import os
import sys
import time
from dotenv import load_dotenv

import requests
import telegram


from exeptions import (
    FailedToMessageError,
    UnexpectedHmWorkStausError,
    RequestAPIError)

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
    logger.info('Пытаемся отправить сообщение в тг.')
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message)
    except telegram.TelegramError:
        raise FailedToMessageError()
    else:
        logger.info(f'Сообщение отправленно: {message}')


def get_api_answer(current_timestamp):
    """Запрашивает инфу по домашкам у API яндекса.
    В случае, если доступно, передает это на обработку
    в другие функции.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    logger.info('Пытаемся получить ответ от API')
    # uncommenting next row allows to get all homeworks
    # params = {'from_date': 1659168456}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params,
        )
    except Exception as error:
        raise RequestAPIError(
            f'Ошибочный запрос к API. Ошибка -{error}'
        )
    if homework_statuses.status_code != 200:
        raise requests.ConnectionError(homework_statuses.status_code)
    return homework_statuses.json()


def check_response(response):
    """Проверяет на то, что ответ API соответствует ожиданиям."""
    if not isinstance(response, dict):
        logger.error('API did not return dictionary')
        raise TypeError('API did not return dictionary')

    if 'homeworks' not in response:
        logger.error('Unexpected return from API: key \'homeworks\' not found')
        raise KeyError(
            'Unexpected return from API: key \'homeworks\' not found')

    if not isinstance(response['homeworks'], list):
        logger.error('API did not return list on homeworks')
        raise TypeError('API did not return list on homeworks')

    return response['homeworks']


def parse_status(homework):
    """Извлекает из информации о конкретной домашке."""
    if 'homework_name' not in homework:
        error_message = 'Ключ homework_name не найден в API'
        raise KeyError(error_message)
    if 'status' not in homework:
        error_message = 'Ключ status не найден в API'
        raise KeyError(error_message)

    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status not in HOMEWORK_STATUSES:
        raise UnexpectedHmWorkStausError()
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем, что токены подключены."""
    empty_token_message = 'Работа программы требует наличия токенов'
    tokens = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    if not all(tokens):
        logger.critical(f' {empty_token_message}')
    return all(tokens)


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Проверь, что подключил токены и указал chat_id'
        sys.exit(message)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    initial_status = ''
    error_message = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
                status = homework[0]['status']
                if status != initial_status:
                    send_message(bot, message)
                    initial_status = status

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

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
