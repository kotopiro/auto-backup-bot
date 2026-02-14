"""
AJS - Advanced Join System
Discord OAuth2 and Member Management Library

A powerful async library for Discord member backup and restoration.
"""

from .core import AJS
from .oauth import OAuth2Handler
from .api import DiscordAPI

__version__ = "1.0.0"
__all__ = ["AJS", "OAuth2Handler", "DiscordAPI"]
