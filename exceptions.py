class QuantityKeyError(Exception):
    """Неверное количество ключей."""

    pass


class TelegramError(Exception):
    """Ошибка в работе телеграм-бота."""

    pass


class HttpStatusError(Exception):
    """Запрос к серверу не выполнен."""

    pass


class TokenNotFound(Exception):
    """Не найдена переменная окружения."""

    pass
