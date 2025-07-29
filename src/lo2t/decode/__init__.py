"""
Functions for decoding GCN notices
"""

from .base import process_gcn_notice
from .ligo import LigoProcessor
from .icecube import IcecubeProcessor
from .einsteinprobe import EinsteinprobeProcessor
from .svom import SvomProcessor
from .swift import SwiftProcessor


LigoProcessor.register()
IcecubeProcessor.register()
EinsteinprobeProcessor.register()
SvomProcessor.register()
SwiftProcessor.register()

__all__ = ["process_gcn_notice"]
