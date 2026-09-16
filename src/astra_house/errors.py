"""Domain-specific ASTRA errors."""


class AstraError(RuntimeError):
    """Base class for expected ASTRA failures."""


class ValidationError(AstraError):
    """Raised when an input or domain model is invalid."""
