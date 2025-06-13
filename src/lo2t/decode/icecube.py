"""
Deciphers IceCube JSON events
"""

from .json_message import JsonMessage


class IcecubeMessage(JsonMessage):
    def __init__(self, message, verbose=False):
        super().__init__(message, verbose)

