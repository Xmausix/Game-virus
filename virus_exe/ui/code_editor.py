import ast
import re
from dataclasses import dataclass


LANGUAGES = ("html", "css", "js", "ts", "python")
SEMANTIC_HTML_TAGS = {"header", "nav", "main", "section", "article", "aside", "footer", "figure", "figcaption", "time"}


@dataclass(frozen=True, slots=True)
class CodeCheck:
    passed: bool
    message: str
    line: int = 0
    category: str = "syntax"


class CodeEditor:
    def __init__(self, source: str = "", language: str = "html") -> None:
        self.language = language if language in LANGUAGES else "html"
        self.lines = source.splitlines() or [""]
        self.row = 0
        self.column = 0
        self.scroll = 0
        self.checks: list[CodeCheck] = []
        self.error_lines: set[int] = set()
        self.preview = ""
        self.message = "F5 CHECK // CTRL+S SAVE // F1 GUIDE"

    @property
    def source(self) -> str:
        return "\n".join(self.lines)

    def set_language(self, language: str) -> None:
        if language in LANGUAGES:
            self.language = language
            self.checks = []
            self.error_lines.clear()
            self.message = f"LANGUAGE SELECTED: {language.upper()}"

    def cycle_language(self, amount: int = 1) -> None:
        index = LANGUAGES.index(self.language)
        self.set_language(LANGUAGES[(index + amount) % len(LANGUAGES)])

    def check(self) -> list[CodeCheck]:
        source = self.source
        if self.language == "python":
            checks = self._check_python(source)
        elif self.language == "html":
            checks = self._check_html(source)
        else:
            checks = self._check_brackets(source, self.language.upper())
        self.checks = checks
        self.error_lines = {check.line for check in checks if not check.passed and check.line > 0}
        passed = all(check.passed for check in checks)
        self.message = "CHECK TRUE // PROGRAM SAFE TO SIMULATE" if passed else "CHECK FALSE // FIX SOURCE ERRORS"
        if self.language == "html" and passed:
            self.preview = source
        return checks

    def _check_python(self, source: str) -> list[CodeCheck]:
        try:
            ast.parse(source or "pass")
            policy_ok = "import os" not in source and "import socket" not in source
            return [
                CodeCheck(True, "PYTHON SYNTAX OK", category="syntax"),
                CodeCheck(policy_ok, "SANDBOX IMPORT POLICY", self._line_with_policy_violation(source), "policy"),
            ]
        except SyntaxError as error:
            return [CodeCheck(False, f"PYTHON LINE {error.lineno}: {error.msg}", error.lineno or 1, "syntax")]

    def _line_with_policy_violation(self, source: str) -> int:
        for number, line in enumerate(source.splitlines(), start=1):
            if "import os" in line or "import socket" in line:
                return number
        return 0

    def _check_html(self, source: str) -> list[CodeCheck]:
        tags = re.finditer(r"<\s*(/?)\s*([a-zA-Z0-9]+)[^>]*>", source)
        stack: list[tuple[str, int]] = []
        void = {"meta", "link", "img", "input", "br", "hr"}
        for match in tags:
            closing, tag = match.group(1), match.group(2).lower()
            line = source.count("\n", 0, match.start()) + 1
            if tag in void:
                continue
            if closing:
                if not stack or stack.pop()[0] != tag:
                    return [CodeCheck(False, f"HTML TAG ORDER ERROR: {tag}", line, "tag")]
            else:
                stack.append((tag, line))
        checks = [CodeCheck(not stack, "HTML TAG BALANCE", stack[-1][1] if stack else 0, "tag"), CodeCheck("<html" in source.lower(), "HTML ROOT PRESENT", self._line_with_text(source, "<html") if "<html" not in source.lower() else 0, "semantic")]
        semantic_found = any(re.search(rf"<\s*{tag}(?:\s|>)", source, re.IGNORECASE) for tag in SEMANTIC_HTML_TAGS)
        checks.append(CodeCheck(True, "SEMANTIC HTML TAGS DETECTED" if semantic_found else "SEMANTIC HTML TAGS OPTIONAL", category="semantic"))
        return checks

    def _line_with_text(self, source: str, value: str) -> int:
        for number, line in enumerate(source.splitlines(), start=1):
            if value.lower() in line.lower():
                return number
        return 1

    def _line_without_semantic_tag(self, source: str) -> int:
        return max(1, len(source.splitlines()))

    def _check_brackets(self, source: str, name: str) -> list[CodeCheck]:
        pairs = {"{": "}", "(": ")", "[": "]"}
        stack: list[tuple[str, int]] = []
        for line_number, line in enumerate(source.splitlines(), start=1):
            for character in line:
                if character in pairs:
                    stack.append((pairs[character], line_number))
                elif character in pairs.values():
                    if not stack or stack.pop()[0] != character:
                        return [CodeCheck(False, f"{name} BRACKET ORDER ERROR", line_number, "syntax")]
        return [CodeCheck(not stack, f"{name} BRACKET BALANCE", stack[-1][1] if stack else 0, "syntax")]

    def highlighted_line(self, line: str) -> list[tuple[str, str]]:
        if self.language == "html":
            return self._highlight_html(line)
        pattern = re.compile(r"(#[^\n]*|//[^\n]*|\"[^\"]*\"|'[^']*'|\b\d+(?:\.\d+)?\b|\b[A-Za-z_][A-Za-z0-9_]*\b|[{}()[\];:,.=+*/<>!-])")
        keywords = {
            "python": {"def", "class", "return", "if", "else", "elif", "for", "while", "in", "import", "from", "as", "True", "False", "None"},
            "js": {"const", "let", "var", "function", "return", "if", "else", "for", "while", "true", "false"},
            "ts": {"const", "let", "var", "function", "return", "interface", "type", "string", "number", "boolean", "true", "false"},
            "css": {"display", "color", "background", "margin", "padding", "font", "width", "height"},
        }.get(self.language, set())
        result: list[tuple[str, str]] = []
        cursor = 0
        for match in pattern.finditer(line):
            if match.start() > cursor:
                result.append((line[cursor:match.start()], "text"))
            value = match.group(0)
            if value.startswith(("#", "//")):
                kind = "comment"
            elif value.startswith(("\"", "'")):
                kind = "string"
            elif value[0].isdigit():
                kind = "number"
            elif value in keywords:
                kind = "keyword"
            else:
                kind = "punctuation"
            result.append((value, kind))
            cursor = match.end()
        if cursor < len(line):
            result.append((line[cursor:], "text"))
        return result or [("", "text")]

    def _highlight_html(self, line: str) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        cursor = 0
        tag_pattern = re.compile(r"<!--.*?-->|</?\s*([a-zA-Z][\w-]*)([^>]*)>")
        for match in tag_pattern.finditer(line):
            if match.start() > cursor:
                result.append((line[cursor:match.start()], "text"))
            if match.group(0).startswith("<!--"):
                result.append((match.group(0), "comment"))
            else:
                tag_name = match.group(1).lower()
                result.append((match.group(0), "semantic" if tag_name in SEMANTIC_HTML_TAGS else "tag"))
            cursor = match.end()
        if cursor < len(line):
            result.append((line[cursor:], "text"))
        return result or [("", "text")]

    def insert(self, value: str) -> None:
        line = self.lines[self.row]
        self.lines[self.row] = line[: self.column] + value + line[self.column :]
        self.column += len(value)
        self.checks = []
        self.error_lines.clear()

    def newline(self) -> None:
        line = self.lines[self.row]
        self.lines[self.row] = line[: self.column]
        self.lines.insert(self.row + 1, line[self.column :])
        self.row += 1
        self.column = 0
        self._ensure_visible()

    def backspace(self) -> None:
        if self.column:
            line = self.lines[self.row]
            self.lines[self.row] = line[: self.column - 1] + line[self.column :]
            self.column -= 1
        elif self.row:
            current = self.lines.pop(self.row)
            self.row -= 1
            self.column = len(self.lines[self.row])
            self.lines[self.row] += current
        self.checks = []
        self.error_lines.clear()
        self._ensure_visible()

    def delete(self) -> None:
        line = self.lines[self.row]
        if self.column < len(line):
            self.lines[self.row] = line[: self.column] + line[self.column + 1 :]
        elif self.row + 1 < len(self.lines):
            self.lines[self.row] += self.lines.pop(self.row + 1)
        self.checks = []
        self.error_lines.clear()

    def move_left(self) -> None:
        if self.column:
            self.column -= 1
        elif self.row:
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
        if self.row >= self.scroll + 26:
            self.scroll = self.row - 25
