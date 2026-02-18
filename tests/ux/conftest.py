"""Fixtures for UX end-to-end tests.

Each fixture produces a small CSV tailored to exercise a specific command's key paths.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import Result
from typer.testing import CliRunner

from csvplot.cli import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Timeline CSV: 10 rows
# - 2 rows share same name (tests composite y / sub-rows)
# - 1 null end (tests --open-end)
# - 3 distinct categories (tests --color)
# - detail column for --y-detail
# - label column for --txt
# ---------------------------------------------------------------------------
TIMELINE_CSV = """\
name,start,end,category,detail,label
Alpha,2024-01-01,2024-01-15,backend,api,Launch
Alpha,2024-02-01,2024-02-20,backend,db,Migration
Bravo,2024-01-10,2024-01-25,frontend,ui,Sprint 1
Charlie,2024-02-10,2024-03-01,backend,api,Refactor
Delta,2024-03-01,2024-03-20,frontend,ui,Sprint 2
Echo,2024-03-15,,backend,api,Ongoing
Foxtrot,2024-01-05,2024-01-20,data,etl,Pipeline
Golf,2024-02-15,2024-03-10,data,etl,Batch
Hotel,2024-01-20,2024-02-05,frontend,ui,Sprint 1.5
India,2024-03-10,2024-03-25,data,ml,Training
"""


@pytest.fixture
def timeline_csv(tmp_path: Path) -> Path:
    p = tmp_path / "timeline.csv"
    p.write_text(TIMELINE_CSV)
    return p


# ---------------------------------------------------------------------------
# Bar CSV: 12 rows
# - 4 distinct statuses with uneven counts (tests sorting)
# - 2 assignees (tests --where filtering)
# - priority column for additional filtering
# ---------------------------------------------------------------------------
BAR_CSV = """\
status,assignee,priority
open,alice,high
open,alice,medium
open,bob,high
open,bob,low
closed,alice,low
closed,bob,medium
closed,charlie,high
in_progress,alice,high
in_progress,bob,medium
blocked,charlie,high
blocked,charlie,low
blocked,alice,medium
"""


@pytest.fixture
def ux_bar_csv(tmp_path: Path) -> Path:
    p = tmp_path / "bar.csv"
    p.write_text(BAR_CSV)
    return p


# ---------------------------------------------------------------------------
# Line CSV: 12 rows
# - 2 regions x 6 dates (tests --color grouping)
# - monotonic dates (tests x-axis ordering)
# - 2 numeric y-columns (tests multi --y)
# ---------------------------------------------------------------------------
LINE_CSV = """\
date,temp,humidity,region
2024-01-01,10.5,60,north
2024-01-02,11.0,62,north
2024-01-03,9.8,58,north
2024-01-04,12.1,65,north
2024-01-05,10.9,61,north
2024-01-06,11.5,63,north
2024-01-01,20.1,70,south
2024-01-02,21.3,72,south
2024-01-03,19.5,68,south
2024-01-04,22.0,74,south
2024-01-05,20.8,71,south
2024-01-06,21.9,73,south
"""


@pytest.fixture
def ux_line_csv(tmp_path: Path) -> Path:
    p = tmp_path / "line.csv"
    p.write_text(LINE_CSV)
    return p


# ---------------------------------------------------------------------------
# Bubble CSV: 10 rows
# - Mix of truthy/falsy values across 3 feature columns
# - 2 categories (tests --color)
# - 1 all-empty row
# ---------------------------------------------------------------------------
BUBBLE_CSV = """\
name,feat_a,feat_b,feat_c,category
Alice,yes,,true,frontend
Bob,no,1,,backend
Charlie,,yes,false,frontend
Dave,yes,yes,true,backend
Eve,,,false,frontend
Frank,yes,no,true,backend
Grace,no,yes,,frontend
Heidi,,,,backend
Ivan,yes,,true,frontend
Judy,no,yes,false,backend
"""


@pytest.fixture
def ux_bubble_csv(tmp_path: Path) -> Path:
    p = tmp_path / "bubble.csv"
    p.write_text(BUBBLE_CSV)
    return p


# ---------------------------------------------------------------------------
# Summarise CSV: 15 rows
# - Numeric col (score), date col (created), text col (notes)
# - 3 nulls, high-cardinality id
# ---------------------------------------------------------------------------
SUMMARISE_CSV = """\
id,name,score,created,notes
1,alice,95.5,2024-01-01,good work
2,bob,82.0,2024-01-02,ok
3,charlie,71.3,2024-01-03,needs improvement
4,dave,,2024-01-04,missing score
5,eve,90.1,2024-01-05,
6,frank,88.2,2024-01-06,solid
7,grace,76.4,,late submission
8,heidi,91.0,2024-01-08,excellent
9,ivan,85.7,2024-01-09,good
10,judy,79.3,2024-01-10,fair
11,kevin,93.2,2024-01-11,outstanding
12,lisa,87.6,2024-01-12,
13,mallory,68.9,2024-01-13,struggles
14,nancy,94.1,2024-01-14,top tier
15,oscar,72.8,2024-01-15,improving
"""


@pytest.fixture
def ux_summarise_csv(tmp_path: Path) -> Path:
    p = tmp_path / "summarise.csv"
    p.write_text(SUMMARISE_CSV)
    return p


# ---------------------------------------------------------------------------
# Dict fixture for parameterized format matrix
# ---------------------------------------------------------------------------
@pytest.fixture
def ux_csvs(
    timeline_csv: Path,
    ux_bar_csv: Path,
    ux_line_csv: Path,
    ux_bubble_csv: Path,
    ux_summarise_csv: Path,
) -> dict[str, Path]:
    return {
        "timeline": timeline_csv,
        "bar": ux_bar_csv,
        "line": ux_line_csv,
        "bubble": ux_bubble_csv,
        "summarise": ux_summarise_csv,
    }


def invoke(*args: str) -> Result:
    """Convenience wrapper around CliRunner.invoke."""
    return runner.invoke(app, list(args))
