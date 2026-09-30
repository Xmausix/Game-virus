from dataclasses import dataclass, field


@dataclass(slots=True)
class InfectionJob:
    node_id: str
    elapsed: float = 0.0
    duration: float = 5.0

    @property
    def progress(self) -> float:
        return min(100.0, self.elapsed / self.duration * 100.0)


@dataclass(slots=True)
class VirusState:
    current_node_id: str = "core"
    selected_node_id: str = "browser"
    hidden_until: float = 0.0
    infection_job: InfectionJob | None = None
    moves: int = 0
    scans: int = 0
    infections: int = 0
    hide_uses: int = 0
    log: list[str] = field(default_factory=list)

    def is_hidden(self, elapsed: float) -> bool:
        return elapsed < self.hidden_until
