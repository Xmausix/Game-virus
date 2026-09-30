from pathlib import Path

from virus_exe.dsl.language import DslTestResult, default_source, test_program


class DslEditor:
    def __init__(self, source: str | None = None) -> None:
        self.lines = (source or default_source()).splitlines() or [""]
        self.row = 0
        self.column = 0
        self.result: DslTestResult | None = None
        self.message = "F5 TEST PROGRAM // F6 APPLY IF TRUE"
        self.scroll = 0

    @property
    def source(self) -> str:
        return "\n".join(self.lines)

    def test(self) -> DslTestResult:
        self.result = test_program(self.source)
        self.message = "TEST TRUE // PROGRAM ACCEPTED" if self.result.passed else "TEST FALSE // FIX ERRORS"
        return self.result

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.source + "\n", encoding="utf-8")
        self.message = "SOURCE SAVED TO DATA/CUSTOM_VIRUS.DSL"

    def insert(self, value: str) -> None:
        line = self.lines[self.row]
        self.lines[self.row] = line[: self.column] + value + line[self.column :]
        self.column += len(value)
        self.result = None

    def newline(self) -> None:
        line = self.lines[self.row]
        self.lines[self.row] = line[: self.column]
        self.lines.insert(self.row + 1, line[self.column :])
        self.row += 1
        self.column = 0
        self.result = None
        self._ensure_visible()

    def backspace(self) -> None:
        if self.column > 0:
            line = self.lines[self.row]
            self.lines[self.row] = line[: self.column - 1] + line[self.column :]
            self.column -= 1
        elif self.row > 0:
            current = self.lines.pop(self.row)
            self.row -= 1
            self.column = len(self.lines[self.row])
            self.lines[self.row] += current
        self.result = None
        self._ensure_visible()

    def delete(self) -> None:
        line = self.lines[self.row]
        if self.column < len(line):
            self.lines[self.row] = line[: self.column] + line[self.column + 1 :]
        elif self.row + 1 < len(self.lines):
            self.lines[self.row] += self.lines.pop(self.row + 1)
        self.result = None

    def move_left(self) -> None:
        if self.column > 0:
            self.column -= 1
        elif self.row > 0:
            self.row -= 1
            self.column = len(self.lines[self.row])
        self._ensure_visible()

    def move_right(self) -> None:
        if self.column < len(self.lines[self.row]):
            self.column += 1
        elif self.row + 1 < len(self.lines):
            self.row += 1
            self.column = 0
        self._ensure_visible()

    def move_up(self) -> None:
        self.row = max(0, self.row - 1)
        self.column = min(self.column, len(self.lines[self.row]))
        self._ensure_visible()

    def move_down(self) -> None:
        self.row = min(len(self.lines) - 1, self.row + 1)
        self.column = min(self.column, len(self.lines[self.row]))
        self._ensure_visible()

    def _ensure_visible(self) -> None:
        if self.row < self.scroll:
            self.scroll = self.row
        if self.row >= self.scroll + 25:
            self.scroll = self.row - 24
