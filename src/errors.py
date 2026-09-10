"""
Slate specific error types.
"""


class SlateError(Exception):
    """Base exception for all Slate errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.message}"


# Backward compatibility alias
DocMindError = SlateError


class ValidationError(SlateError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        details: dict | None = None,
        error_code: str = "VALIDATION_ERROR",
    ) -> None:
        super().__init__(message, error_code=error_code, details=details)


class IngestionError(SlateError):
    """Raised when document ingestion/processing fails."""

    def __init__(
        self,
        message: str,
        details: dict | None = None,
        error_code: str = "INGESTION_ERROR",
    ) -> None:
        super().__init__(message, error_code=error_code, details=details)


class RetrievalError(SlateError):
    """Raised when document retrieval fails."""

    def __init__(
        self,
        message: str,
        details: dict | None = None,
        error_code: str = "RETRIEVAL_ERROR",
    ) -> None:
        super().__init__(message, error_code=error_code, details=details)


class GenerationError(SlateError):
    """Raised when answer generation fails."""

    def __init__(
        self,
        message: str,
        details: dict | None = None,
        error_code: str = "GENERATION_ERROR",
    ) -> None:
        super().__init__(message, error_code=error_code, details=details)


class AuthenticationError(SlateError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str,
        details: dict | None = None,
        error_code: str = "AUTHENTICATION_ERROR",
    ) -> None:
        super().__init__(message, error_code=error_code, details=details)


class ConfigurationError(SlateError):
    """Raised when there is a configuration issue."""

    def __init__(
        self,
        message: str,
        details: dict | None = None,
        error_code: str = "CONFIGURATION_ERROR",
    ) -> None:
        super().__init__(message, error_code=error_code, details=details)


class ExternalServiceError(SlateError):
    """Raised when an external service call fails."""

    def __init__(
        self,
        message: str,
        details: dict | None = None,
        error_code: str = "EXTERNAL_SERVICE_ERROR",
    ) -> None:
        super().__init__(message, error_code=error_code, details=details)
