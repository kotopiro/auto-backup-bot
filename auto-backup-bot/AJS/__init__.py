"""
AJS - Advanced Join System
Discord OAuth2 and Member Management Library

A powerful async library for Discord member backup and restoration.
"""

from .core import AJS

__version__ = "1.0.0"
__all__ = ["AJS"]

# Optional imports
try:
    from .oauth import OAuth2Handler
    __all__.append("OAuth2Handler")
except ImportError:
    pass

try:
    from .api import DiscordAPI
    __all__.append("DiscordAPI")
except ImportError:
    pass
