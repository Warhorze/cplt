"""Format matrix: 5 commands x 3 formats = 15 parameterized cases.

Each case asserts:
- exit_code == 0
- stdout is non-empty
- No Python tracebacks in output
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.ux.conftest import invoke

# Minimum required args per command (csv path filled dynamically).
COMMAND_ARGS: dict[str, list[str]] = {
    "timeline": ["--x", "start", "--x", "end", "--y", "name"],
    "bar": ["-c", "status"],
    "line": ["--x", "date", "--y", "temp"],
    "bubble": ["--cols", "feat_a", "--cols", "feat_b", "--y", "name"],
    "summarise": [],
}

FORMATS = ["visual", "compact", "semantic"]


@pytest.mark.parametrize("command", COMMAND_ARGS.keys())
@pytest.mark.parametrize("fmt", FORMATS)
def test_format_acceptance(command: str, fmt: str, ux_csvs: dict[str, Path]) -> None:
    """Every command x format combination exits cleanly with non-empty output."""
    csv_path = str(ux_csvs[command])
    args = [command, "-f", csv_path] + COMMAND_ARGS[command] + ["--format", fmt]
    result = invoke(*args)

    assert result.exit_code == 0, f"exit_code={result.exit_code}\n{result.stdout}"
    assert result.stdout.strip(), "stdout was empty"
    assert "Traceback" not in result.stdout, f"Traceback in output:\n{result.stdout}"
