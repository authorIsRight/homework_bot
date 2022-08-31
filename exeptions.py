class FailedToMessageError(Exception):
    """Не удалось отправить сообщение."""

    pass


class UnexpectedHmWorkStausError(Exception):
    """Неожиданный статус домашки."""

    pass


class RequestAPIError(Exception):
    """Ошибка запроса к API."""
