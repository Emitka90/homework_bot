import logging
import os
import sys
import time
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import HttpStatusError, QuantityKeyError, TelegramError

load_dotenv()


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler = StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TOKENS = [PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN]
TOKENS_STR = ['PRACTICUM_TOKEN', 'TELEGRAM_CHAT_ID', 'TELEGRAM_TOKEN']

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
RETRY_PERIOD = 600

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    token_list = []
    for token in TOKENS_STR:
        if not globals()[token]:
            token_list.append(token)
    if len(token_list) > 0:
        logger.critical(
            f'Отсутствует обязательная переменная окружения: '
            f'{", ".join(token_list)}'
            f'Программа принудительно остановлена.'
        )
        return False


def send_message(bot, message):
    """Отправка сообщения в Telegram-чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
    except TelegramError as error:
        logger.error('Не удалось отправить сообщение')
        raise TelegramError(f'Не удалось отправить сообщение {error}')
    else:
        logging.debug(f'Сообщение отправлено {message}')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API сервиса."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=timestamp)
        if response.status_code != 200:
            logger.error(f'API недоступен, код состояния ответа: '
                         f'{response.status_code}')
            raise HttpStatusError(f'API недоступен, код состояния ответа: '
                                  f'{response.status_code}')
    except Exception as error:
        logger.error(f'Сбой при запросе к эндпоинту: {error}')
        raise error('Сбой при запросе к эндпоинту')
    response = response.json()
    return response


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        logger.error('Неверный тип данных в ответе API')
        raise TypeError('Неверный тип данных в ответе API')
    if len(response) < 2:
        logger.error(
            f'Неверное количество ключей в ответе API: {len(response)}'
        )
        raise QuantityKeyError('Неверное количество ключей в ответе API')
    if 'homeworks' and 'current_date' not in response:
        logger.error('Отсутствие ожидаемых ключей в ответе API')
        raise QuantityKeyError('Отсутствие ожидаемых ключей в ответе API')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        logger.error(
            f'Неверный тип данных списка домашних работ: {type(homeworks)}'
        )
        raise TypeError('Неверный тип данных в ответе API')
    return homeworks


def parse_status(homework):
    """Проверяем статус работы и возвращаем ответ."""
    if not isinstance(homework, dict):
        logger.error(
            f'Неверный тип данных элемента списка домашних работ: '
            f'{type(homework)}'
        )
        raise TypeError('Неверный тип данных в ответе API')
    if 'homework_name' not in homework:
        logger.error('Отсутствует ключ "homework_name" в ответе API')
        raise KeyError('Нет данных для проверки статуса')
    if 'status' not in homework:
        logger.error('Отсутствует ключ "status" в ответе API')
        raise KeyError('Нет данных для проверки статуса')
    else:
        homework_name = homework.get('homework_name')
        status = homework.get('status')
        if status not in HOMEWORK_VERDICTS:
            logger.error(
                f'Неожиданный статус домашней работы, '
                f'обнаруженный в ответе API: {status}'
            )
            raise HttpStatusError(
                'Неожиданный статус домашней работы, обнаруженный в ответе API'
            )
        else:
            verdict = HOMEWORK_VERDICTS[status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        sys.exit(1)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''
    last_error = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            timestamp = response.get('current_date')
            if not homeworks:
                logger.info('Работа не взята на проверку')
            else:
                homework = homeworks[0]
                message = parse_status(homework)
                if message == last_message:
                    logger.info('Статус не обновлен')
                    continue
                else:
                    last_message = message
                    send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if last_error != str(error):
                last_error = str(error)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
