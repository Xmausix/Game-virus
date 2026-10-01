import re
from dataclasses import dataclass
from operator import eq, ge, gt, le, lt

from virus_exe.virus.catalog import AttackMethod, VirusProfile, method_by_id


OPERATORS = {">": gt, ">=": ge, "<": lt, "<=": le, "==": eq}
SIGNALS = {"DETECTION", "SECURITY", "CPU", "NETWORK", "INFECTION"}
ACTIONS = {"HIDE", "ATTACK", "MOVE", "WAIT"}
TOOL_TYPES = {"EXPLOIT", "BACKDOOR", "PAYLOAD", "WORM"}


@dataclass(frozen=True, slots=True)
class DslRule:
    signal: str
    operator: str
    threshold: float
    action: str
    argument: str | None = None

    def matches(self, values: dict[str, float]) -> bool:
        value = values.get(self.signal, 0.0)
        return OPERATORS[self.operator](value, self.threshold)


@dataclass(frozen=True, slots=True)
class CustomTool:
    tool_id: str
    tool_type: str
    power: float
    noise: float
    cost: float
    remote: bool

    @property
    def method_id(self) -> str:
        return f"custom:{self.tool_id.lower()}"

    def attack_method(self) -> AttackMethod:
        return AttackMethod(
            method_id=self.method_id,
            label=self.tool_id,
            description=f"fikcyjny modul typu {self.tool_type}",
            base_success=min(0.94, 0.52 + self.power / 250.0),
            infection_gain=12.0 + self.power * 0.42,
            duration=max(2.8, 6.4 - self.power / 28.0),
            noise=self.noise,
            cpu_cost=max(1.0, self.cost),
            network_cost=3.0 if self.remote else 1.0,
            remote=self.remote,
            cooldown=4.0 + self.cost * 0.3,
            intel_cost=1.0 if self.remote else 0.0,
            requires_analysis=True,
        )


@dataclass(frozen=True, slots=True)
class CustomVirusProgram:
    name: str
    power: float
    stealth: float
    spread: float
    persistence: float
    default_method: str
    rules: tuple[DslRule, ...]
    tools: tuple[CustomTool, ...]
    source: str

    @property
    def profile(self) -> VirusProfile:
        stealth_value = self.stealth / 100.0
        return VirusProfile(
            virus_id="custom",
            code_name=self.name,
            description="wirus zbudowany w edytorze gracza",
            power=self.power / 100.0,
            stealth=stealth_value,
            spread=self.spread / 100.0,
            persistence=self.persistence / 100.0,
            detection_modifier=max(0.45, 1.35 - stealth_value * 0.45),
        )


@dataclass(frozen=True, slots=True)
class DslTestResult:
    passed: bool
    program: CustomVirusProgram | None
    checks: tuple[tuple[bool, str], ...]
    errors: tuple[str, ...]


_HEADER_PATTERN = re.compile(r"^VIRUS\s+([A-Z][A-Z0-9_-]{1,15})$", re.IGNORECASE)
_RULE_PATTERN = re.compile(
    r"^RULE\s+(DETECTION|SECURITY|CPU|NETWORK|INFECTION)\s*(>=|<=|==|>|<)\s*(\d+(?:\.\d+)?)\s+THEN\s+(HIDE|ATTACK|MOVE|WAIT)(?:\s+([A-Z][A-Z0-9_-]*))?$",
    re.IGNORECASE,
)
_TOOL_PATTERN = re.compile(
    r"^TOOL\s+([A-Z][A-Z0-9_-]{1,15})\s+TYPE\s+(EXPLOIT|BACKDOOR|PAYLOAD|WORM)\s+POWER\s+(\d+(?:\.\d+)?)\s+NOISE\s+(\d+(?:\.\d+)?)\s+COST\s+(\d+(?:\.\d+)?)\s+RANGE\s+(LOCAL|REMOTE)$",
    re.IGNORECASE,
)


def compile_program(source: str) -> tuple[CustomVirusProgram | None, tuple[str, ...]]:
    errors: list[str] = []
    lines = source.splitlines()
    name: str | None = None
    values: dict[str, float] = {}
    method = "exploit"
    rules: list[DslRule] = []
    tools: list[CustomTool] = []
    ended = False
    seen_fields: set[str] = set()
    seen_tools: set[str] = set()

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue
        header = _HEADER_PATTERN.fullmatch(line)
        if header:
            if name is not None:
                errors.append(f"LINE {line_number}: DUPLICATE VIRUS HEADER")
            name = header.group(1).upper()
            continue
        if line.upper() == "END":
            ended = True
            continue
        field_match = re.fullmatch(r"(POWER|STEALTH|SPREAD|PERSISTENCE)\s+(\d+(?:\.\d+)?)", line, re.IGNORECASE)
        if field_match:
            field = field_match.group(1).upper()
            if field in seen_fields:
                errors.append(f"LINE {line_number}: DUPLICATE FIELD {field}")
            seen_fields.add(field)
            value = float(field_match.group(2))
            if not 0.0 <= value <= 100.0:
                errors.append(f"LINE {line_number}: {field} MUST BE BETWEEN 0 AND 100")
            values[field] = value
            continue
        tool_match = _TOOL_PATTERN.fullmatch(line)
        if tool_match:
            tool_id = tool_match.group(1).upper()
            if tool_id in seen_tools:
                errors.append(f"LINE {line_number}: DUPLICATE TOOL {tool_id}")
            seen_tools.add(tool_id)
            tool_type = tool_match.group(2).upper()
            power = float(tool_match.group(3))
            noise = float(tool_match.group(4))
            cost = float(tool_match.group(5))
            remote = tool_match.group(6).upper() == "REMOTE"
            if not 0.0 <= power <= 100.0:
                errors.append(f"LINE {line_number}: TOOL POWER MUST BE BETWEEN 0 AND 100")
            if not 0.0 <= noise <= 100.0:
                errors.append(f"LINE {line_number}: TOOL NOISE MUST BE BETWEEN 0 AND 100")
            if not 1.0 <= cost <= 20.0:
                errors.append(f"LINE {line_number}: TOOL COST MUST BE BETWEEN 1 AND 20")
            tools.append(CustomTool(tool_id, tool_type, power, noise, cost, remote))
            continue
        method_match = re.fullmatch(r"METHOD\s+([A-Z][A-Z0-9_-]*)", line, re.IGNORECASE)
        if method_match:
            method = method_match.group(1).lower()
            continue
        rule_match = _RULE_PATTERN.fullmatch(line)
        if rule_match:
            action = rule_match.group(4).upper()
            argument = rule_match.group(5).lower() if rule_match.group(5) else None
            if action == "ATTACK" and argument is None:
                errors.append(f"LINE {line_number}: ATTACK NEEDS A METHOD")
            if action == "ATTACK" and argument and method_by_id(argument) is None and argument.upper() not in seen_tools:
                errors.append(f"LINE {line_number}: UNKNOWN ATTACK METHOD {argument.upper()}")
            if action != "ATTACK" and argument is not None:
                errors.append(f"LINE {line_number}: ONLY ATTACK ACCEPTS AN ARGUMENT")
            rules.append(DslRule(rule_match.group(1).upper(), rule_match.group(2), float(rule_match.group(3)), action, argument))
            continue
        errors.append(f"LINE {line_number}: UNKNOWN INSTRUCTION")

    if name is None:
        errors.append("MISSING VIRUS HEADER")
    if not ended:
        errors.append("MISSING END")
    for field in ("POWER", "STEALTH", "SPREAD", "PERSISTENCE"):
        if field not in values:
            errors.append(f"MISSING FIELD {field}")
    if not rules:
        errors.append("AT LEAST ONE RULE IS REQUIRED")
    tool_ids = {tool.tool_id.lower() for tool in tools}
    if method not in tool_ids and method_by_id(method) is None:
        errors.append(f"UNKNOWN DEFAULT METHOD {method.upper()}")
    if len(tools) > 4:
        errors.append("MAXIMUM 4 TOOLS ALLOWED")

    if errors or name is None:
        return None, tuple(errors)
    program = CustomVirusProgram(name, values["POWER"], values["STEALTH"], values["SPREAD"], values["PERSISTENCE"], method, tuple(rules), tuple(tools), source)
    return program, ()


def test_program(source: str) -> DslTestResult:
    program, errors = compile_program(source)
    if program is None:
        return DslTestResult(False, None, tuple(), errors)
    checks: list[tuple[bool, str]] = []
    checks.append((0.0 <= program.power <= 100.0, "POWER RANGE"))
    checks.append((0.0 <= program.stealth <= 100.0, "STEALTH RANGE"))
    checks.append((0.0 <= program.spread <= 100.0, "SPREAD RANGE"))
    checks.append((0.0 <= program.persistence <= 100.0, "PERSISTENCE RANGE"))
    checks.append((len(program.tools) > 0, "FICTIONAL TOOL EXISTS"))
    checks.append((len(program.tools) <= 4, "TOOL COUNT <= 4"))
    checks.append((method_by_id(program.default_method) is not None or program.default_method in {tool.tool_id.lower() for tool in program.tools}, "DEFAULT METHOD EXISTS"))
    checks.append((len(program.rules) <= 8, "RULE COUNT <= 8"))
    test_values = {"DETECTION": 75.0, "SECURITY": 45.0, "CPU": 35.0, "NETWORK": 65.0, "INFECTION": 20.0}
    triggered = sum(1 for rule in program.rules if rule.matches(test_values))
    checks.append((triggered > 0, "SIMULATION TRIGGERS A RULE"))
    passed = all(result for result, _ in checks)
    return DslTestResult(passed, program, tuple(checks), ())


def default_source() -> str:
    return "\n".join(
        [
            "VIRUS CUSTOM_GHOST",
            "POWER 62",
            "STEALTH 86",
            "SPREAD 48",
            "PERSISTENCE 22",
            "TOOL GHOSTLINK TYPE BACKDOOR POWER 58 NOISE 7 COST 2 RANGE REMOTE",
            "TOOL PACKET_RIFT TYPE EXPLOIT POWER 72 NOISE 15 COST 4 RANGE LOCAL",
            "METHOD GHOSTLINK",
            "RULE DETECTION > 60 THEN HIDE",
            "RULE SECURITY < 70 THEN ATTACK GHOSTLINK",
            "END",
        ]
    )
