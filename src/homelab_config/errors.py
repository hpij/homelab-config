"""Public error types for invalid canonical configuration and selection."""


class HomelabConfigError(ValueError):
    """Base class for deterministic configuration failures."""


class ConfigurationError(HomelabConfigError):
    """The canonical repository configuration is missing or contradictory."""


class SelectionError(HomelabConfigError):
    """A requested canonical host or appliance selection is invalid."""
