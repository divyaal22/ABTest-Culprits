"""
A/B Test Cross-Platform Diagnostic Framework

This package provides tools to diagnose and identify issues in cross-platform A/B tests.
"""

from .diagnostics import ABTestDiagnostics
from .analyzer import CrossPlatformAnalyzer
from .reports import DiagnosticReport
from .data_prep import (
    DataPreparation,
    validate_user_level,
    aggregate_to_user_level,
    prepare_from_events
)

__version__ = "0.1.0"
__all__ = [
    "ABTestDiagnostics",
    "CrossPlatformAnalyzer",
    "DiagnosticReport",
    "DataPreparation",
    "validate_user_level",
    "aggregate_to_user_level",
    "prepare_from_events"
]
