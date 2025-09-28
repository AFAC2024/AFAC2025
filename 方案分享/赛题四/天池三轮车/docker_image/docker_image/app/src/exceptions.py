class ToolError(Exception):
    """Raised when a tool encounters an error."""

    def __init__(self, message):
        self.message = message


class TokenLimitExceeded(Exception):
    """Exception raised when the token limit is exceeded"""
