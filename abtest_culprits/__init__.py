"""
A/B Test Cross-Platform Diagnostic Framework

This package provides tools to diagnose and identify issues in cross-platform A/B tests.
"""

from .diagnostics import ABTestDiagnostics
from .analyzer import CrossPlatformAnalyzer
from .reports import DiagnosticReport

__version__ = "0.1.0"
__all__ = ["ABTestDiagnostics", "CrossPlatformAnalyzer", "DiagnosticReport"]
