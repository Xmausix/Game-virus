from dataclasses import dataclass, field

from virus_exe.core.models import SystemGraph
from virus_exe.missions.model import Mission, MissionResult
from virus_exe.security.model import SecurityState
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
    _history_elapsed: float = 0.0
    _saved: bool = False

    def __post_init__(self) -> None:
        self.graph.get_node("core").discovered = True
        self.graph.get_node(self.virus.current_node_id).discovered = True
        for node_id in self.graph.neighbors(self.virus.current_node_id):
            self.graph.get_node(node_id).discovered = True
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

    def select_node(self, node_id: str) -> None:
        if node_id not in self.graph.nodes:
            return
        self.virus.selected_node_id = node_id
        node = self.graph.get_node(node_id)
        if node.discovered:
            self.add_message(f"TARGET LOCKED: {node.name}")
        else:
            self.add_message("TARGET DATA UNKNOWN - SCAN REQUIRED")

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
        self.security.add_detection(1.0 + firewall_cost)
        for node_id in self.graph.neighbors(target):
            self.graph.get_node(node_id).discovered = True
        self.add_message(f"MOVED: {target_node.name}")

    def infect(self) -> None:
        if not self.is_playing:
            return
        if self.virus.current_node_id == "core":
            self.add_message("INFECTION BLOCKED: CORE IS READ-ONLY")
            return
        if self.virus.infection_job is not None:
            self.add_message("INFECTION ALREADY RUNNING")
            return
        node = self.current_node
        if node.infection >= 100.0:
            self.add_message("INFECTION SKIPPED: MODULE ALREADY CONTROLLED")
            return
        duration = max(3.5, 6.5 - node.security / 30.0)
        self.virus.infection_job = InfectionJob(node_id=node.node_id, duration=duration)
        self.cpu = min(100.0, self.cpu + 8.0)
        self.network = min(100.0, self.network + 4.0)
        self.security.add_detection(5.0)
        self.add_message(f"INFECTION STARTED: {node.name}")

    def hide(self) -> None:
        if not self.is_playing:
            return
        self.virus.hidden_until = max(self.virus.hidden_until, self.elapsed + 4.5)
        self.virus.hide_uses += 1
        self.cpu = min(100.0, self.cpu + 1.0)
        self.security.reduce_detection(8.0)
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
            infection_rate = 100.0 / job.duration
            node.add_infection(infection_rate * dt)
            multiplier = 0.2 if hidden else 1.0
            self.security.add_detection((0.75 + node.security / 100.0 * 1.15) * dt * multiplier)
            self.cpu = min(100.0, self.cpu + dt * 1.1)
            self.network = min(100.0, self.network + dt * 0.5)
            if self.scan_target_id == node.node_id and not hidden:
                self.security.add_detection(dt * 1.25)
            if job.elapsed >= job.duration:
                self.virus.infection_job = None
                self.virus.infections += 1
                node.infection = 100.0
                self.add_message(f"INFECTION COMPLETE: {node.name}")
        elif not hidden and self.security.detection > 0:
            self.security.add_detection(dt * 0.08)

        self._check_end_conditions()

    def _check_end_conditions(self) -> None:
        if self.security.detection >= 100.0:
            self.status = "LOST"
            self.end_reason = "SYSTEM COMPROMISED AND PURGED"
            self.add_message("SYSTEM PURGE INITIATED")
            return
        if self.security.detection >= self.mission.detection_limit:
            self.status = "LOST"
            self.end_reason = "STEALTH LIMIT EXCEEDED"
            self.add_message("ANTIVIRUS PURGED THE PROCESS")
            return
        if self.objectives_complete:
            self.status = "WON"
            self.end_reason = "ALL LEVEL OBJECTIVES COMPLETE"
            self.add_message("LEVEL COMPLETE")

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
        return int(1000.0 + stealth_bonus + time_bonus + infection_bonus + level_bonus)
