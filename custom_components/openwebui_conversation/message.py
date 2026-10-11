"""Message representation for OpenWebUI conversation history."""

from time import time_ns


class Message:
    """Represent a conversation message with its creation timestamp."""

    def __init__(self, role: str, message: str) -> None:
        """Initialize a message with the current timestamp."""
        self.timestamp = time_ns()
        self.role = role
        self.message = message

    def __str__(self) -> str:
        """Return the role, timestamp, and message as a string."""
        return f"{self.role} @ {self.timestamp} : {self.message}"
