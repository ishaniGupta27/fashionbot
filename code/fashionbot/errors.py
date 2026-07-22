class FashionbotError(RuntimeError):
    """User-facing error that should be printed without a traceback."""


class VTOContentPolicyError(FashionbotError):
    """A provider rejected one VTO item because of content policy checks."""


class VTOProviderError(FashionbotError):
    """A provider failed a VTO call for a non-recoverable reason."""
