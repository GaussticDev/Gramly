class TelegramError(Exception):
    def __init__(self, description: str, errorCode: int = 0, retryAfter: int | None = None):
        super().__init__(description)
        self.description = description
        self.errorCode = errorCode
        self.retryAfter = retryAfter

    def __repr__(self):
        return f"TelegramError({self.description!r}, code={self.errorCode}, retry_after={self.retryAfter})"
