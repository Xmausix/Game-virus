import random
import shlex
from dataclasses import dataclass, field

from virus_exe.core.models import SystemGraph
from virus_exe.dsl.language import CustomVirusProgram, DslRule
from virus_exe.missions.model import Mission, MissionResult
from virus_exe.security.model import SecurityState
from virus_exe.virus.catalog import ATTACK_METHODS, VIRUS_PROFILES, AttackMethod, VirusProfile, method_by_id, virus_by_id
from virus_exe.virus.model import InfectionJob, VirusState


@dataclass(slots=True)
class GameState:
    graph: SystemGraph
    mission: Mission
    level_index: int = 1
    total_levels: int = 1
    virus: VirusState = field(default_factory=VirusState)
    security: SecurityState = field(default_factory=SecurityState)
    elapsed: float = 0.0
    cpu: float = 42.0
    memory: float = 38.0
    network: float = 24.0
    status: str = "PLAYING"
    end_reason: str = ""
    history: list[tuple[float, float]] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    console_lines: list[str] = field(default_factory=list)
    _history_elapsed: float = 0.0
    _saved: bool = False
    _rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        self.graph.get_node("core").discovered = True
        self.graph.get_node(self.virus.current_node_id).discovered = True
        for node_id in self.graph.neighbors(self.virus.current_node_id):
            self.graph.get_node(node_id).discovered = True
        self.console_write("VIRUS.EXE TACTICAL SHELL 2.0")
        self.console_write("TYPE HELP FOR AVAILABLE COMMANDS")
        self.add_message("KERNEL LINK ESTABLISHED")
        self.add_message(f"LEVEL {self.level_index:02d}: {self.mission.title}")
        self.add_message(f"OBJECTIVE: {self.mission.briefing.upper()}")

    @property
    def is_playing(self) -> bool:
        return self.status == "PLAYING"

    @property
    def current_node(self):
        return self.graph.get_node(self.virus.current_node_id)

    @property
    def selected_node(self):
        return self.graph.get_node(self.virus.selected_node_id)

    @property
    def virus_profile(self) -> VirusProfile:
        if self.virus.selected_virus_id == "custom" and self.virus.custom_profile is not None:
            return self.virus.custom_profile
        return virus_by_id(self.virus.selected_virus_id) or VIRUS_PROFILES[0]

    @property
    def attack_method(self) -> AttackMethod:
        return method_by_id(self.virus.selected_method_id) or ATTACK_METHODS[0]

    @property
    def scan_target_id(self) -> str:
        nodes = [node.node_id for node in self.graph.nodes.values() if node.node_id != "core"]
        return nodes[self.security.scan_index % len(nodes)] if nodes else "core"

    @property
    def objective_progress(self) -> list[tuple[object, float, bool]]:
        result = []
        for objective in self.mission.objectives:
            node = self.graph.get_node(objective.node_id)
            progress = min(100.0, node.infection / objective.infection * 100.0)
            result.append((node, progress, node.infection >= objective.infection))
        return result

    @property
    def objectives_complete(self) -> bool:
        return all(item[2] for item in self.objective_progress)

    def add_message(self, message: str) -> None:
        self.messages.append(f"{self.elapsed:06.2f}  {message}")
        self.messages = self.messages[-7:]
        self.virus.log.append(message)
        self.virus.log = self.virus.log[-40:]

    def console_write(self, line: str) -> None:
        self.console_lines.append(line.upper())
        self.console_lines = self.console_lines[-14:]

    def select_node(self, node_id: str) -> None:
        if node_id not in self.graph.nodes:
            return
        self.virus.selected_node_id = node_id
        node = self.graph.get_node(node_id)
        if node.discovered:
            self.add_message(f"TARGET LOCKED: {node.name}")
            self.console_write(f"TARGET = {node.node_id}")
        else:
            self.add_message("TARGET DATA UNKNOWN - SCAN REQUIRED")
            self.console_write("TARGET DATA UNKNOWN")

    def select_virus(self, virus_id: str) -> bool:
        profile = self.virus.custom_profile if virus_id == "custom" else virus_by_id(virus_id)
        if profile is None:
            self.console_write("UNKNOWN VIRUS PROFILE")
            return False
        self.virus.selected_virus_id = virus_id
        self.console_write(f"VIRUS PROFILE LOADED: {profile.code_name}")
        self.add_message(f"VIRUS PROFILE: {profile.code_name}")
        return True

    def apply_custom_program(self, program: CustomVirusProgram) -> None:
        self.virus.custom_profile = program.profile
        self.virus.custom_rules = program.rules
        self.virus.selected_virus_id = "custom"
        self.virus.selected_method_id = program.default_method
        self.virus.automation = False
        self.virus.rule_cooldowns.clear()
        self.console_write(f"CUSTOM VIRUS LOADED: {program.name}")
        self.console_write(f"DEFAULT METHOD: {program.default_method.upper()}")
        self.add_message(f"CUSTOM VIRUS LOADED: {program.name}")

    def select_method(self, method_id: str) -> bool:
        method = method_by_id(method_id)
        if method is None:
            self.console_write("UNKNOWN ATTACK METHOD")
            return False
        self.virus.selected_method_id = method.method_id
        self.console_write(f"ATTACK METHOD ARMED: {method.label}")
        self.add_message(f"METHOD ARMED: {method.label}")
        return True

    def scan(self) -> None:
        if not self.is_playing:
            return
        for node in self.graph.nodes.values():
            node.discovered = True
        self.virus.scans += 1
        self.cpu = min(100.0, self.cpu + 2.0)
        self.network = min(100.0, self.network + 3.0)
        self.security.add_detection(1.0)
        self.add_message(f"SYSTEM SCAN COMPLETE: {len(self.graph.nodes)} NODES FOUND")

    def move(self) -> None:
        if not self.is_playing:
            return
        source = self.virus.current_node_id
        target = self.virus.selected_node_id
        if source == target:
            self.add_message("MOVE ABORTED: ALREADY IN TARGET")
            return
        if not self.graph.is_connected(source, target):
            self.add_message("MOVE BLOCKED: NO ACTIVE CONNECTION")
            return
        target_node = self.graph.get_node(target)
        if target_node.isolated:
            self.add_message("MOVE BLOCKED: MODULE ISOLATED")
            return
        connection = self.graph.connection_between(source, target)
        firewall_cost = (connection.firewall / 12.0) if connection else 0.0
        self.virus.current_node_id = target
        self.virus.moves += 1
        self.cpu = min(100.0, self.cpu + 2.0)
        self.network = min(100.0, self.network + 2.0 + firewall_cost)
        self.security.add_detection((1.0 + firewall_cost) * self.virus_profile.detection_modifier)
        for node_id in self.graph.neighbors(target):
            self.graph.get_node(node_id).discovered = True
        self.add_message(f"MOVED: {target_node.name}")

    def attack(self, method_id: str | None = None) -> bool:
        if method_id:
            self.select_method(method_id)
        if not self.is_playing:
            return False
        if self.virus.infection_job is not None:
            self.console_write("ATTACK REJECTED: PROCESS ALREADY RUNNING")
            self.add_message("ATTACK ALREADY RUNNING")
            return False
        method = self.attack_method
        profile = self.virus_profile
        target = self.selected_node if method.remote else self.current_node
        if target.node_id == "core":
            self.console_write("ATTACK REJECTED: CORE IS READ-ONLY")
            self.add_message("ATTACK BLOCKED: CORE IS READ-ONLY")
            return False
        if target.infection >= 100.0:
            self.console_write("ATTACK SKIPPED: TARGET ALREADY CONTROLLED")
            return False
        if method.remote:
            if target.node_id == self.current_node.node_id:
                self.console_write("LATERAL REQUIRES A DIFFERENT TARGET")
                return False
            if not self.graph.is_connected(self.current_node.node_id, target.node_id):
                self.console_write("LATERAL BLOCKED: NO ACTIVE CONNECTION")
                self.add_message("REMOTE ATTACK BLOCKED: NO ACTIVE CONNECTION")
                return False
        if method.category and target.category != method.category:
            self.console_write(f"METHOD REQUIRES CATEGORY: {method.category.upper()}")
            self.add_message("ATTACK BLOCKED: TARGET CATEGORY INVALID")
            return False
        if method.required_virus and profile.virus_id != method.required_virus:
            self.console_write(f"METHOD REQUIRES VIRUS: {method.required_virus.upper()}")
            self.add_message("ATTACK BLOCKED: VIRUS PROFILE INCOMPATIBLE")
            return False

        success_chance = max(0.15, min(0.97, method.base_success + profile.power * 0.12 - target.security / 100.0 * 0.20))
        planned_gain = method.infection_gain * (0.75 + profile.power * 0.22 + profile.spread * 0.12)
        duration = max(2.8, method.duration - profile.power * 0.8)
        self.virus.infection_job = InfectionJob(
            node_id=target.node_id,
            method_id=method.method_id,
            duration=duration,
            planned_gain=planned_gain,
            success_chance=success_chance,
            starting_infection=target.infection,
        )
        self.virus.attacks += 1
        self.cpu = min(100.0, self.cpu + method.cpu_cost)
        self.network = min(100.0, self.network + method.network_cost)
        self.security.add_detection(method.noise * profile.detection_modifier * 0.45)
        if method.method_id == "spoof":
            self.security.reduce_detection(4.0 + profile.stealth * 3.0)
        self.console_write(f"ATTACK STARTED: {method.label} -> {target.name}")
        self.console_write(f"SUCCESS PROBABILITY: {success_chance * 100:04.1f}%")
        self.add_message(f"{method.label} STARTED: {target.name}")
        return True

    def infect(self) -> None:
        self.attack()

    def hide(self) -> None:
        if not self.is_playing:
            return
        profile = self.virus_profile
        duration = 4.5 + profile.stealth * 2.0
        reduction = 8.0 + profile.stealth * 5.0
        self.virus.hidden_until = max(self.virus.hidden_until, self.elapsed + duration)
        self.virus.hide_uses += 1
        self.cpu = min(100.0, self.cpu + 1.0)
        self.security.reduce_detection(reduction)
        self.console_write(f"STEALTH CLOAK ACTIVE FOR {duration:04.1f}s")
        self.add_message("STEALTH MODE ACTIVE")

    def update(self, dt: float) -> None:
        if not self.is_playing:
            return
        dt = max(0.0, min(dt, 0.1))
        self.elapsed += dt
        self.cpu = max(18.0, self.cpu - dt * 2.2)
        self.memory = min(100.0, max(20.0, self.memory + dt * 0.18))
        self.network = max(12.0, self.network - dt * 0.7)
        self._history_elapsed += dt
        if self._history_elapsed >= 0.5:
            self.history.append((self.elapsed, self.security.detection))
            self.history = self.history[-180:]
            self._history_elapsed = 0.0

        self.security.scan_elapsed += dt
        if self.security.scan_elapsed >= self.security.scan_duration:
            self.security.scan_elapsed = 0.0
            self.security.scan_index += 1
            self.add_message(f"ANTIVIRUS TARGET: {self.graph.get_node(self.scan_target_id).name}")

        hidden = self.virus.is_hidden(self.elapsed)
        if self.virus.infection_job is not None:
            job = self.virus.infection_job
            job.elapsed += dt
            node = self.graph.get_node(job.node_id)
            method = method_by_id(job.method_id) or ATTACK_METHODS[0]
            profile = self.virus_profile
            infection_rate = job.planned_gain / job.duration
            node.add_infection(infection_rate * dt)
            detection_rate = (0.55 + node.security / 100.0 * 0.80) * profile.detection_modifier
            detection_rate *= 0.2 if hidden else 1.0
            detection_rate *= max(0.35, method.noise / 8.0) if method.noise > 0 else 0.35
            self.security.add_detection(detection_rate * dt)
            self.cpu = min(100.0, self.cpu + dt * 1.1)
            self.network = min(100.0, self.network + dt * 0.5)
            if self.scan_target_id == node.node_id and not hidden:
                self.security.add_detection(dt * 1.25)
            if job.elapsed >= job.duration:
                self.virus.infection_job = None
                if self._rng.random() <= job.success_chance:
                    self.virus.infections += 1
                    node.infection = min(100.0, max(node.infection, job.starting_infection + job.planned_gain))
                    if method.method_id == "persist":
                        self.virus.persistence = True
                    self.console_write(f"ATTACK SUCCESS: {method.label} / {node.name}")
                    self.add_message(f"ATTACK SUCCESS: {node.name}")
                else:
                    node.infection = job.starting_infection
                    self.console_write(f"ATTACK FAILED: {method.label} / TRACE LEFT")
                    self.add_message(f"ATTACK FAILED: {node.name}")
        elif not hidden and self.security.detection > 0:
            self.security.add_detection(dt * 0.08 * self.virus_profile.detection_modifier)

        self._run_custom_rules()
        self._check_end_conditions()

    def _run_custom_rules(self) -> None:
        if not self.virus.automation or not self.virus.custom_rules or not self.is_playing:
            return
        values = {
            "DETECTION": self.security.detection,
            "SECURITY": float(self.current_node.security),
            "CPU": self.cpu,
            "NETWORK": self.network,
            "INFECTION": self.current_node.infection,
        }
        for index, rule in enumerate(self.virus.custom_rules):
            if self.virus.rule_cooldowns.get(index, 0.0) > self.elapsed:
                continue
            if not isinstance(rule, DslRule) or not rule.matches(values):
                continue
            if rule.action == "HIDE":
                self.hide()
            elif rule.action == "ATTACK":
                self.attack(rule.argument)
            elif rule.action == "MOVE":
                self.move()
            self.virus.rule_cooldowns[index] = self.elapsed + 3.0
            self.console_write(f"AUTO RULE {index + 1}: {rule.action}")
            break

    def execute_command(self, command: str) -> list[str]:
        raw = command.strip()
        if not raw:
            return []
        self.console_write(f"$ {raw}")
        try:
            parts = shlex.split(raw.lower())
        except ValueError:
            self.console_write("SYNTAX ERROR")
            return ["SYNTAX ERROR"]
        verb, args = parts[0], parts[1:]
        output: list[str] = []
        if verb in {"help", "?"}:
            output = [
                "HELP  STATUS  SCAN  NODES  VIRUSES  METHODS",
                "TARGET <NODE>  VIRUS <ID>  METHOD <ID>",
                "MOVE  ATTACK [METHOD]  HIDE  AUTO  EDITOR  CLEAR",
            ]
        elif verb == "status":
            output = [
                f"VIRUS={self.virus_profile.code_name} METHOD={self.attack_method.label} AUTO={self.virus.automation}",
                f"CURRENT={self.current_node.node_id} TARGET={self.selected_node.node_id}",
                f"DETECTION={self.security.detection:04.1f}% CPU={self.cpu:04.1f}%",
            ]
        elif verb == "scan":
            self.scan()
            output = ["SCAN COMPLETE"]
        elif verb in {"nodes", "targets"}:
            output = [f"{node.node_id:<10} {node.name:<12} INF={node.infection:03.0f}%" for node in self.graph.nodes.values()]
        elif verb in {"viruses", "virus-list"}:
            output = [f"{profile.virus_id:<10} {profile.code_name:<8} {profile.description}" for profile in VIRUS_PROFILES]
            if self.virus.custom_profile is not None:
                output.append(f"custom     {self.virus.custom_profile.code_name:<8} editor build")
        elif verb in {"methods", "attacks", "attack-list"}:
            output = [f"{method.method_id:<10} {method.label:<9} {method.description}" for method in ATTACK_METHODS]
        elif verb in {"target", "select-target"}:
            output = ["USAGE: TARGET <NODE>"] if not args else self._command_target(args[0])
        elif verb in {"virus", "select-virus"}:
            output = ["USAGE: VIRUS <ID>"] if not args else ["VIRUS SELECTED" if self.select_virus(args[0]) else "VIRUS NOT FOUND"]
        elif verb in {"method", "select-method"}:
            output = ["USAGE: METHOD <ID>"] if not args else ["METHOD SELECTED" if self.select_method(args[0]) else "METHOD NOT FOUND"]
        elif verb == "move":
            if args:
                self._command_target(args[0])
            self.move()
            output = [f"CURRENT NODE: {self.current_node.node_id}"]
        elif verb in {"attack", "infect"}:
            output = ["ATTACK QUEUED" if self.attack(args[0] if args else None) else "ATTACK REJECTED"]
        elif verb in {"auto", "autopilot"}:
            if self.virus.custom_profile is None:
                output = ["LOAD A CUSTOM VIRUS FIRST"]
            else:
                self.virus.automation = not self.virus.automation
                output = [f"AUTOPILOT {'ON' if self.virus.automation else 'OFF'}"]
        elif verb == "hide":
            self.hide()
            output = ["STEALTH ACTIVE"]
        elif verb == "clear":
            self.console_lines.clear()
            output = ["CONSOLE BUFFER CLEARED"]
        elif verb in {"editor", "edit"}:
            output = ["EDITOR IS CONTROLLED BY THE UI: PRESS E"]
        else:
            output = ["COMMAND NOT FOUND: TYPE HELP"]
        for line in output:
            self.console_write(line)
        return output

    def _command_target(self, value: str) -> list[str]:
        node = next(
            (
                item
                for item in self.graph.nodes.values()
                if item.node_id == value or item.short_name.lower() == value or item.name.lower() == value
            ),
            None,
        )
        if node is None:
            self.console_write("TARGET NOT FOUND")
            return ["TARGET NOT FOUND"]
        self.select_node(node.node_id)
        return [f"TARGET SELECTED: {node.node_id}"]

    def _check_end_conditions(self) -> None:
        if self.security.detection >= 100.0:
            self.status = "LOST"
            self.end_reason = "SYSTEM COMPROMISED AND PURGED"
            self.add_message("SYSTEM PURGE INITIATED")
            self.console_write("SYSTEM PURGE INITIATED")
            return
        if self.security.detection >= self.mission.detection_limit:
            self.status = "LOST"
            self.end_reason = "STEALTH LIMIT EXCEEDED"
            self.add_message("ANTIVIRUS PURGED THE PROCESS")
            self.console_write("ANTIVIRUS PURGED THE PROCESS")
            return
        if self.objectives_complete:
            self.status = "WON"
            self.end_reason = "ALL LEVEL OBJECTIVES COMPLETE"
            self.add_message("LEVEL COMPLETE")
            self.console_write("LEVEL COMPLETE")

    def result(self) -> MissionResult:
        score = self.calculate_score() if self.status == "WON" else 0
        return MissionResult(
            status=self.status,
            reason=self.end_reason,
            score=score,
            duration=round(self.elapsed, 2),
            total_infection=round(self.graph.total_infection(), 2),
            detection=round(self.security.detection, 2),
            moves=self.virus.moves,
            scans=self.virus.scans,
            infections=self.virus.infections,
            hides=self.virus.hide_uses,
        )

    def calculate_score(self) -> int:
        stealth_bonus = max(0.0, 100.0 - self.security.detection) * 10.0
        time_bonus = max(0.0, 600.0 - self.elapsed) * 2.0
        infection_bonus = self.graph.total_infection() * 3.0
        level_bonus = self.level_index * 250.0
        attack_bonus = self.virus.attacks * 15.0
        return int(1000.0 + stealth_bonus + time_bonus + infection_bonus + level_bonus + attack_bonus)
