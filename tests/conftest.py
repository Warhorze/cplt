"""Shared test fixtures."""

from __future__ import annotations

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


BAR_CSV = """\
status,assignee,priority
open,alice,high
closed,bob,low
open,alice,medium
open,charlie,high
closed,alice,low
"""

LINE_CSV = """\
date,temperature,humidity,region
2024-01-01,10.5,60,north
2024-01-02,11.0,62,north
2024-01-03,9.8,58,north
2024-01-01,20.1,70,south
2024-01-02,21.3,72,south
2024-01-03,19.5,68,south
"""

NUMERIC_CSV = """\
name,score,grade,notes
alice,95.5,A,good
bob,82,B,ok
charlie,not_a_number,C,bad
dave,,D,missing
"""


@pytest.fixture
def bar_csv(tmp_path: Path) -> Path:
    """Write a bar-chart CSV to a temp file and return its path."""
    p = tmp_path / "bar.csv"
    p.write_text(BAR_CSV)
    return p


@pytest.fixture
def line_csv(tmp_path: Path) -> Path:
    """Write a line-chart CSV to a temp file and return its path."""
    p = tmp_path / "line.csv"
    p.write_text(LINE_CSV)
    return p


@pytest.fixture
def numeric_csv(tmp_path: Path) -> Path:
    """Write a CSV with mixed numeric/non-numeric columns."""
    p = tmp_path / "numeric.csv"
    p.write_text(NUMERIC_CSV)
    return p


HIST_CSV = """\
name,score,grade
alice,95.5,A
bob,82.0,B
charlie,71.3,C
dave,,D
eve,90.1,A
frank,88.2,B
grace,76.4,C
heidi,91.0,A
ivan,85.7,B
judy,79.3,C
kevin,93.2,A
lisa,87.6,B
mallory,68.9,C
nancy,94.1,A
oscar,72.8,C
pete,not_a_number,F
quincy,80.0,B
rose,86.5,B
sam,77.1,C
tina,92.4,A
"""


@pytest.fixture
def hist_csv(tmp_path: Path) -> Path:
    p = tmp_path / "hist.csv"
    p.write_text(HIST_CSV)
    return p


@pytest.fixture
def real_csv() -> Path:
    """Path to the real sample data file."""
    return Path(__file__).parent.parent / "data" / "timeplot.csv"
