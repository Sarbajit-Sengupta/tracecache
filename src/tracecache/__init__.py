"""Offline analysis of initially empty, equal-sized-object caches."""

from .profile import LRUProfile, profile_lru
from .simulate import simulate

__all__ = ["LRUProfile", "profile_lru", "simulate"]
__version__ = "0.1.0"
