"""Typed errors for the Meridian evaluation pipeline."""


class MeridianError(Exception):
    """Base error for everything this package raises."""


class ValidationError(MeridianError):
    """Raised when input data fails validation."""


class NotFoundError(MeridianError):
    """Raised when a requested record does not exist."""


class ConfigurationError(MeridianError):
    """Raised when the setup is incomplete or inconsistent."""
