"""Shared test fixtures."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import pytest

SAMPLE_CSV = """\
name,start,end,category,color
task1,2024-01-01 00:00:00,2024-01-10 00:00:00,A,red
task2,2024-02-01,2024-02-15,B,blue
task3,2024-03-01 12:00:00.000,9999-12-31 00:00:00.000,A,red
task4,2024-04-01,,B,blue
task5,,2024-05-01,A,green
"""


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """Write a sample CSV to a temp file and return its path."""
    p = tmp_path / "test.csv"
    p.write_text(SAMPLE_CSV)
    return p


@pytest.fixture
def real_csv() -> Path:
    """Path to the real sample data file."""
    return Path(__file__).parent.parent / "data" / "timeplot.csv"
