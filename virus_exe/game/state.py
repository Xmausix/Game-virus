import random
import shlex
from dataclasses import dataclass, field

from virus_exe.core.models import SystemGraph
from virus_exe.core.vfs import VirtualFileSystem
from virus_exe.dsl.language import CustomVirusProgram, DslRule
from virus_exe.missions.model import Mission, MissionResult
from virus_exe.missions.tasks import TaskManager
from virus_exe.security.model import SecurityState
from virus_exe.virus.catalog import ATTACK_METHODS, VIRUS_PROFILES, AttackMethod, VirusProfile, method_by_id, virus_by_id
from virus_exe.virus.model import InfectionJob, VirusState


@dataclass(frozen=True, slots=True)
class ClientOrder:
    order_id: str
    title: str
    client: str
    description: str
    language: str
    cost: int
    reward: int


CLIENT_ORDERS: tuple[ClientOrder, ...] = (
    ClientOrder("order:ghost-page", "GHOST LANDING PAGE", "GHOST", "Zbuduj bezpieczna strone startowa w symulacji.", "html", 20, 36),
    ClientOrder("order:crt-style", "CRT STYLE PACK", "NIGHT SHIFT", "Przygotuj arkusz stylow dla panelu retro.", "css", 24, 42),
    ClientOrder("order:task-script", "TASK SCRIPT", "HANDLER", "Napisz statycznie sprawdzony skrypt listy zadan.", "js", 28, 48),
    ClientOrder("order:typed-config", "TYPED CONFIG", "ARCHIVIST", "Przygotuj typowany opis konfiguracji laboratorium.", "ts", 32, 54),
    ClientOrder("order:report-tool", "REPORT TOOL", "ANALYST", "Zaprojektuj bezpieczny parser raportu danych.", "python", 36, 60),
)


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
    intel: float = 0.0
    cooldowns: dict[str, float] = field(default_factory=dict)
    world_events: list[str] = field(default_factory=list)
    isolation_until: dict[str, float] = field(default_factory=dict)
    tasks: TaskManager = field(default_factory=TaskManager)
    addresses: dict[str, str] = field(default_factory=dict)
    assigned_address: str = ""
    network_mapped: bool = False
    data_extracted: bool = False
    event_flags: set[str] = field(default_factory=set)
    code_checks: set[str] = field(default_factory=set)
    shop_purchases: set[str] = field(default_factory=set)
    active_order: str = ""
    completed_orders: set[str] = field(default_factory=set)
    vfs: VirtualFileSystem = field(default_factory=VirtualFileSystem)
    _history_elapsed: float = 0.0
    _world_elapsed: float = 0.0
    _saved: bool = False
    _rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        self.graph.get_node("core").discovered = True
        self.graph.get_node(self.virus.current_node_id).discovered = True
        for node_id in self.graph.neighbors(self.virus.current_node_id):
            self.graph.get_node(node_id).discovered = True
        for index, node_id in enumerate(self.graph.nodes, start=10):
            self.addresses[node_id] = f"SIM://{self.graph.name}/10.7.0.{index}"
        self.console_write("VIRUS.EXE TACTICAL SHELL 2.0")
        self.console_write("TYPE HELP FOR AVAILABLE COMMANDS")
        self.add_message("KERNEL LINK ESTABLISHED")
        self.add_message(f"SESSION: {self.mission.title}")
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
        return self._method_by_id(self.virus.selected_method_id) or ATTACK_METHODS[0]

    def _method_by_id(self, method_id: str) -> AttackMethod | None:
        return self.virus.custom_methods.get(method_id) or method_by_id(method_id)

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

    def world_event(self, event: str) -> None:
        self.world_events.append(event)
        self.world_events = self.world_events[-8:]
        self.console_write(f"WORLD: {event}")
        self.add_message(event)

    def emit_event(self, event: str) -> None:
        self.event_flags.add(event)

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
        self.emit_event(f"virus:{virus_id}")
        self.console_write(f"VIRUS PROFILE LOADED: {profile.code_name}")
        self.add_message(f"VIRUS PROFILE: {profile.code_name}")
        return True

    def apply_custom_program(self, program: CustomVirusProgram) -> None:
        self.virus.custom_profile = program.profile
        self.emit_event("custom:virus")
        self.virus.custom_methods = {tool.method_id: tool.attack_method() for tool in program.tools}
        if program.tools:
            self.emit_event("custom:tool")
        self.virus.custom_rules = program.rules
        self.virus.selected_virus_id = "custom"
        default_method_id = f"custom:{program.default_method}" if program.default_method in {tool.tool_id.lower() for tool in program.tools} else program.default_method
        self.virus.selected_method_id = default_method_id
        self.virus.automation = False
        self.virus.rule_cooldowns.clear()
        self.console_write(f"CUSTOM VIRUS LOADED: {program.name}")
        self.console_write(f"DEFAULT METHOD: {program.default_method.upper()}")
        self.add_message(f"CUSTOM VIRUS LOADED: {program.name}")

    def select_method(self, method_id: str) -> bool:
        normalized = method_id.lower()
        method = self._method_by_id(normalized) or self._method_by_id(f"custom:{normalized}")
        if method is None:
            self.console_write("UNKNOWN ATTACK METHOD")
            return False
        self.virus.selected_method_id = method.method_id
        self.emit_event(f"method:{method.method_id.split(':')[-1]}")
        self.console_write(f"ATTACK METHOD ARMED: {method.label}")
        self.add_message(f"METHOD ARMED: {method.label}")
        return True

    def scan(self) -> None:
        if not self.is_playing:
            return
        for node in self.graph.nodes.values():
            node.discovered = True
        self.virus.scans += 1
        self.emit_event("scan")
        self.intel = min(100.0, self.intel + 4.0)
        self.cpu = min(100.0, self.cpu + 2.0)
        self.network = min(100.0, self.network + 3.0)
        self.security.add_detection(1.0)
        self.add_message(f"SYSTEM SCAN COMPLETE: {len(self.graph.nodes)} NODES FOUND")
        self.world_event("SCAN SIGNATURE ADDED TO SECURITY LOG")

    def analyze(self) -> None:
        if not self.is_playing:
            return
        target = self.selected_node
        if not target.discovered:
            self.console_write("ANALYSIS BLOCKED: SCAN TARGET FIRST")
            return
        if target.analyzed:
            self.console_write("ANALYSIS CACHE HIT")
            self.intel = min(100.0, self.intel + 1.0)
            return
        target.analyzed = True
        self.emit_event("analyze")
        self.emit_event(f"analyze:{target.node_id}")
        self.intel = min(100.0, self.intel + 8.0)
        self.cpu = min(100.0, self.cpu + 3.0)
        self.security.add_detection(1.5)
        self.console_write(f"ANALYSIS COMPLETE: {target.name}")
        self.console_write(f"VULNERABILITY={target.vulnerability:02d} PROCESSES={len(target.processes)}")
        self.add_message(f"TARGET ANALYZED: {target.name}")

    def discover_network(self) -> None:
        if not self.is_playing:
            return
        for node in self.graph.nodes.values():
            node.discovered = True
        self.emit_event("discover")
        self.intel = min(100.0, self.intel + 6.0)
        self.console_write("SIMULATION DISCOVERY COMPLETE")
        for node_id, address in self.addresses.items():
            self.console_write(f"{address}  {node_id.upper()}")
        self.world_event("SYNTHETIC NETWORK INVENTORY CREATED")

    def map_network(self) -> None:
        if not self.is_playing:
            return
        if not all(node.discovered for node in self.graph.nodes.values()):
            self.console_write("MAP INCOMPLETE: RUN DISCOVER FIRST")
            return
        self.network_mapped = True
        self.emit_event("map")
        if any(connection.firewall for connection in self.graph.connections):
            self.emit_event("map:firewall")
        self.intel = min(100.0, self.intel + 8.0)
        self.console_write("SYNTHETIC TOPOLOGY MAPPED")
        for connection in self.graph.connections:
            self.console_write(f"{connection.source.upper()} <-> {connection.target.upper()} FW={connection.firewall:02d}")
        self.world_event("ROUTE TABLE UPDATED IN SIMULATION")

    def assign_address(self, value: str) -> None:
        node = next((item for item in self.graph.nodes.values() if item.node_id == value or item.short_name.lower() == value or item.name.lower() == value), None)
        if node is None:
            self.console_write("ADDRESS TARGET NOT FOUND")
            return
        if not node.discovered:
            self.console_write("ADDRESS TARGET UNKNOWN: DISCOVER FIRST")
            return
        self.select_node(node.node_id)
        self.assigned_address = self.addresses[node.node_id]
        self.emit_event("assign")
        if node.node_id == "files" and node.infection >= 100.0 and not self.data_extracted:
            self.emit_event("files:prepared")
        if node.node_id == "files" and self.data_extracted:
            self.emit_event("final:assign")
        self.console_write(f"TARGET ADDRESS ASSIGNED: {self.assigned_address}")

    def extract_data(self) -> None:
        if not self.is_playing:
            return
        files = self.graph.get_node("files")
        if files.infection < 100.0:
            self.console_write("EXTRACTION BLOCKED: FILES CONTROL REQUIRED")
            return
        if self.assigned_address != self.addresses.get("files"):
            self.console_write("EXTRACTION BLOCKED: ASSIGN FILES ADDRESS FIRST")
            return
        self.data_extracted = True
        self.emit_event("extraction")
        self.intel = min(100.0, self.intel + 10.0)
        self.console_write("TEST DATA EXTRACTED FROM SIMULATION")
        self.world_event("EXTRACTION WINDOW CLOSED")

    def hint(self) -> None:
        self.console_write(f"HINT: {self.tasks.hint()}")

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
        if self.cooldowns.get(method.method_id, 0.0) > self.elapsed:
            remaining = self.cooldowns[method.method_id] - self.elapsed
            self.console_write(f"METHOD COOLDOWN: {remaining:04.1f}s")
            return False
        if self.intel < method.intel_cost:
            self.console_write(f"INSUFFICIENT INTEL: NEED {method.intel_cost:04.1f}")
            return False
        if target.isolated:
            self.console_write("ATTACK BLOCKED: TARGET ISOLATED")
            self.add_message("ATTACK BLOCKED: TARGET ISOLATED")
            return False
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

        analysis_bonus = 0.12 if target.analyzed else -0.10 if method.requires_analysis else 0.0
        vulnerability_bonus = target.vulnerability / 100.0 * 0.12
        success_chance = max(0.15, min(0.97, method.base_success + profile.power * 0.12 + vulnerability_bonus + analysis_bonus - target.security / 100.0 * 0.20))
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
        self.intel = max(0.0, self.intel - method.intel_cost)
        self.cooldowns[method.method_id] = self.elapsed + method.cooldown
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
        self.emit_event("hide")
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
        self._world_elapsed += dt
        self._world_simulation()

        hidden = self.virus.is_hidden(self.elapsed)
        if self.virus.infection_job is not None:
            job = self.virus.infection_job
            job.elapsed += dt
            node = self.graph.get_node(job.node_id)
            method = self._method_by_id(job.method_id) or ATTACK_METHODS[0]
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
                        self.emit_event("persistence")
                    self.emit_event(f"attack:{method.method_id.split(':')[-1]}")
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

    def _world_simulation(self) -> None:
        for node_id, until in list(self.isolation_until.items()):
            if until <= self.elapsed:
                self.graph.get_node(node_id).isolated = False
                del self.isolation_until[node_id]
                self.world_event(f"MODULE RESTORED: {node_id.upper()}")
        if self._world_elapsed < 7.0:
            return
        self._world_elapsed = 0.0
        active_nodes = [node for node in self.graph.nodes.values() if node.node_id != "core"]
        for node in active_nodes:
            if node.user_activity > 0:
                node.user_activity = max(0, min(100, node.user_activity + self._rng.randint(-4, 5)))
        if self.security.detection >= 70.0 and not self.isolation_until:
            candidate = max(active_nodes, key=lambda node: node.detection + node.security * 0.3)
            candidate.isolated = True
            self.isolation_until[candidate.node_id] = self.elapsed + 8.0
            self.world_event(f"SECURITY ISOLATION: {candidate.name}")
        else:
            active_user = max((node for node in active_nodes if node.category == "user"), key=lambda node: node.user_activity, default=None)
            if active_user and active_user.user_activity >= 70:
                active_user.vulnerability = min(100, active_user.vulnerability + 3)
                self.world_event(f"USER ACTIVITY SPIKE: {active_user.name}")

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

    def vfs_command(self, verb: str, args: list[str]) -> list[str]:
        if verb in {"dir", "ls"}:
            return [f"{kind.upper():4} {name}" for name, kind in self.vfs.list_dir()]
        if verb == "pwd":
            return [self.vfs.cwd_path]
        if verb == "cd":
            if not args or not self.vfs.cd(args[0]):
                return ["DIRECTORY NOT FOUND"]
            self.emit_event("vfs:cd")
            return [f"CURRENT DIRECTORY: {self.vfs.cwd_path}"]
        if verb == "mkdir":
            if not args or not self.vfs.mkdir(args[0]):
                return ["MKDIR FAILED"]
            self.emit_event("vfs:mkdir")
            return [f"DIRECTORY CREATED: {args[0]}"]
        if verb in {"touch", "newfile"}:
            if not args or not self.vfs.touch(args[0]):
                return ["FILE CREATE FAILED"]
            self.emit_event("vfs:touch")
            if args[0].lower().endswith(".html"):
                self.emit_event("vfs:file:html")
            if args[0].lower().endswith(".code"):
                self.emit_event("vfs:file:code")
            return [f"FILE CREATED: {args[0]}"]
        if verb == "write":
            if len(args) < 2 or not self.vfs.write(args[0], " ".join(args[1:])):
                return ["WRITE FAILED"]
            self.emit_event("vfs:write")
            return [f"FILE WRITTEN: {args[0]}"]
        if verb == "cat":
            if not args:
                return ["USAGE: CAT <FILE>"]
            content = self.vfs.read(args[0])
            return [content] if content is not None else ["FILE NOT FOUND"]
        if verb == "tree":
            self.emit_event("vfs:tree")
            return self.vfs.tree()
        return ["VFS COMMAND NOT FOUND"]

    def install_package(self, package: str) -> bool:
        allowed = {"editor-pro", "syntax-pack", "sim-network", "file-tools"}
        if package not in allowed:
            return False
        self.shop_purchases.add(package)
        self.emit_event(f"shop:{package}")
        return True

    def order_by_id(self, order_id: str) -> ClientOrder | None:
        return next((order for order in CLIENT_ORDERS if order.order_id == order_id), None)

    def accept_order(self, order_id: str) -> bool:
        order = self.order_by_id(order_id)
        if order is None or order.order_id in self.completed_orders or self.active_order:
            return False
        if self.tasks.reputation < order.cost:
            self.console_write(f"ORDER REJECTED: NEED {order.cost} REP")
            return False
        self.tasks.reputation -= order.cost
        self.active_order = order.order_id
        self.emit_event("order:accepted")
        self.console_write(f"ORDER ACCEPTED: {order.title}")
        return True

    def submit_order(self, order_id: str) -> bool:
        order = self.order_by_id(order_id)
        if order is None or self.active_order != order.order_id or order.language not in self.code_checks:
            self.console_write("ORDER BLOCKED: REQUIRED CODE CHECK IS MISSING")
            return False
        self.completed_orders.add(order.order_id)
        self.active_order = ""
        self.tasks.reputation += order.reward
        self.tasks.xp += order.reward
        self.tasks.level = 1 + self.tasks.xp // 100
        self.emit_event(f"order:complete:{order.order_id}")
        self.console_write(f"ORDER COMPLETE: REP +{order.reward}")
        return True

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
        if verb in {"dir", "ls", "pwd", "cd", "mkdir", "touch", "newfile", "write", "cat", "tree"}:
            output = self.vfs_command(verb, args)
        elif verb in {"help", "?"}:
            output = [
                "HELP  STATUS  SCAN  ANALYZE  DISCOVER  MAP  ADDRESSES",
                "TASKS  HINT  TARGET <NODE>  ASSIGN <NODE>  PROBE <NODE>",
                "DIR  CD  PWD  MKDIR  TOUCH  WRITE  CAT  TREE",
                "VIRUSES  METHODS  MOVE  ATTACK  EXTRACT  AUTO  EDITOR  ORDERS",
            ]
        elif verb == "status":
            output = [
                f"VIRUS={self.virus_profile.code_name} METHOD={self.attack_method.label} AUTO={self.virus.automation}",
                f"CURRENT={self.current_node.node_id} TARGET={self.selected_node.node_id}",
                f"DETECTION={self.security.detection:04.1f}% CPU={self.cpu:04.1f}% INTEL={self.intel:04.1f}",
                f"TASK={self.tasks.current.task_id if self.tasks.current else 'COMPLETE'} ADDRESS={self.assigned_address or 'NONE'}",
            ]
        elif verb == "scan":
            self.scan()
            output = ["SCAN COMPLETE"]
        elif verb in {"analyze", "analyse", "probe"}:
            if verb == "probe" and args:
                self._command_target(args[0])
            self.analyze()
            output = ["ANALYSIS COMPLETE"]
        elif verb in {"nmap", "sim-nmap", "scan-net"}:
            self.discover_network()
            self.emit_event("sim:nmap")
            output = ["SIMULATED NMAP COMPLETE // NO REAL NETWORK ACCESS"]
        elif verb in {"nslookup", "sim-nslookup", "dig"}:
            self.emit_event("sim:nslookup")
            target = args[0] if args else self.selected_node.node_id
            output = [f"SIM DNS {target.upper()} -> {self.addresses.get(target, 'UNKNOWN SIM ADDRESS')}"]
        elif verb in {"dighunter", "sim-dighunter"}:
            self.emit_event("sim:dighunter")
            output = ["DIG HUNTER PUZZLE: FIND THE SERVICE WITH THE LOWEST FIREWALL SCORE"]
        elif verb in {"discover", "discovery"}:
            self.discover_network()
            output = ["DISCOVERY COMPLETE"]
        elif verb in {"map", "topology"}:
            self.map_network()
            output = ["MAP COMPLETE" if self.network_mapped else "MAP INCOMPLETE"]
        elif verb in {"addresses", "address"}:
            output = [f"{node_id:<10} {address}" for node_id, address in self.addresses.items()]
        elif verb in {"assign", "route"}:
            if args:
                self.assign_address(args[0])
            output = [f"ASSIGNED {self.assigned_address or 'NONE'}"]
        elif verb in {"tasks", "taskbar"}:
            output = [f"{'>' if task is self.tasks.current else 'OK' if task.task_id in self.tasks.completed else '--'} {task.title}: {task.description}" for task in self.tasks.tasks]
        elif verb in {"orders", "jobs", "contracts"}:
            output = [f"{order.order_id} {order.title} LANG={order.language.upper()} COST={order.cost} REWARD={order.reward}" for order in CLIENT_ORDERS]
        elif verb in {"accept-order", "accept-job"}:
            output = ["ORDER ACCEPTED" if args and self.accept_order(args[0]) else "ORDER NOT ACCEPTED"]
        elif verb in {"submit-order", "submit-job"}:
            output = ["ORDER COMPLETE" if args and self.submit_order(args[0]) else "ORDER NOT COMPLETE"]
        elif verb in {"hint", "clue"}:
            self.hint()
            output = ["HINT ISSUED"]
        elif verb in {"nodes", "targets"}:
            output = [f"{node.node_id:<10} {node.name:<12} INF={node.infection:03.0f}% VULN={node.vulnerability:02d} ANALYZED={node.analyzed}" for node in self.graph.nodes.values()]
        elif verb in {"viruses", "virus-list"}:
            output = [f"{profile.virus_id:<10} {profile.code_name:<8} {profile.description}" for profile in VIRUS_PROFILES]
            if self.virus.custom_profile is not None:
                output.append(f"custom     {self.virus.custom_profile.code_name:<8} editor build")
        elif verb in {"methods", "attacks", "attack-list"}:
            output = [f"{method.method_id:<18} {method.label:<12} {method.description}" for method in ATTACK_METHODS]
            output.extend(f"{method.method_id:<18} {method.label:<12} {method.description}" for method in self.virus.custom_methods.values())
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
                if self.virus.automation:
                    self.emit_event("auto:on")
                output = [f"AUTOPILOT {'ON' if self.virus.automation else 'OFF'}"]
        elif verb in {"extract", "collect"}:
            self.extract_data()
            output = ["EXTRACTION COMPLETE" if self.data_extracted else "EXTRACTION BLOCKED"]
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

    def _update_tasks(self) -> None:
        completed = self.tasks.update(self)
        if completed:
            self.emit_event(f"task:{completed.task_id}")
            self.console_write(f"TASK COMPLETE: {completed.title} // REP +{completed.reward}")
            next_task = self.tasks.current.title if self.tasks.current else "SESSION COMPLETE"
            self.world_event(f"TASK UNLOCKED: {next_task}")

    def _check_end_conditions(self) -> None:
        self._update_tasks()
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
        if self.tasks.all_complete:
            self.status = "WON"
            self.end_reason = "ALL TASKS COMPLETE"
            self.add_message("CAMPAIGN COMPLETE")
            self.console_write("CAMPAIGN COMPLETE")

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
