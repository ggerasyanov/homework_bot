import logging
import os
import time
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

import log_messages as log

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='main.log',
    filemode='w'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('main.log', maxBytes=50000000, backupCount=5)
logger.addHandler(handler)

load_dotenv()
try:
    PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    CHAT_ID = os.getenv('CHAT_ID')
except Exception:
    logging.critical(log.LOG_EMPTY_TOKEN)
    raise Exception({log.LOG_EMPTY_TOKEN})

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}


def send_error_message(bot, message, error=''):
    """Отправляет сообщение в телеграм если возникает ошибка в работе бота."""
    options_message = [
        log.LOG_ACCESS_ENDPOINT_ERROR,
        log.LOG_REQUEST_FAILED_ERROR,
        log.LOG_REQUEST_KEY_ERROR,
    ]
    if message in options_message:
        request = f'Ошибка: {message}, {error}'
        options_message.remove(message)
    bot.send_message(CHAT_ID, request)


def send_message(bot, message):
    """Отправляет сообщение в чат бота."""
    try:
        bot.send_message(CHAT_ID, message)
        logging.info(log.LOG_SEND_MESSAGE)
    except Exception:
        logging.error(log.LOG_SEND_MESSAGE_ERROR)


def parse_status(homeworks):
    """Подготавливает ответ для отправки ботом."""
    try:
        status = homeworks['status']
    except Exception:
        logging.error(log.LOG_REQUEST_KEY_ERROR)
        raise KeyError(log.LOG_REQUEST_KEY_ERROR)
    try:
        homework_name = homeworks['homework_name']
    except Exception:
        logging.error(log.LOG_REQUEST_KEY_ERROR)
        raise KeyError(log.LOG_REQUEST_KEY_ERROR)
    verdict = HOMEWORK_STATUSES[status]
    return (f'Изменился статус проверки работы "{homework_name}".'
            f'{verdict}')


def check_response(response):
    """Проверяет изменение статуса домашней работы."""
    try:
        current_date = response['current_date']
    except Exception:
        logging.error(log.LOG_REQUEST_KEY_ERROR)
        raise KeyError(log.LOG_REQUEST_KEY_ERROR)
    if response['homeworks'] == []:
        logging.info(log.LOG_STATUS_NOT_CHANGED)
        return {
            'homeworks': '',
            'current_date': current_date
        }
    if response['homeworks'][0]['status'] not in HOMEWORK_STATUSES.keys():
        logging.error(log.LOG_REQUEST_KEY_ERROR)
        raise KeyError(log.LOG_REQUEST_KEY_ERROR)
    return response


def get_api_answer(url, current_timestamp):
    """Делает запрос к API и передаёт результат."""
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': current_timestamp}
    try:
        response = requests.get(url, headers=headers, params=payload)
        status_code = response.status_code
    except Exception as error:
        logging.error(log.LOG_REQUEST_FAILED_ERROR)
        raise ConnectionResetError(f'{log.LOG_REQUEST_FAILED_ERROR}'
                                   f'{error}')
    if status_code != 200:
        logging.error(log.LOG_ACCESS_ENDPOINT_ERROR)
        raise ConnectionResetError(log.LOG_ACCESS_ENDPOINT_ERROR)
    return response.json()


def main():
    """Основная исполняющая функция кода, которая запускает вечный цикл."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            result_check_response = check_response(get_api_answer(
                ENDPOINT,
                current_timestamp
            ))
            if result_check_response['homeworks'] != '':
                message = parse_status(result_check_response['homeworks'][0])
                send_message(bot, message)
            current_timestamp = result_check_response['current_date']
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = error
            send_error_message(bot, message)
            time.sleep(RETRY_TIME)
            continue


if __name__ == '__main__':
    main()
