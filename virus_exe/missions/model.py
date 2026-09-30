from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MissionObjective:
    node_id: str
    infection: float


@dataclass(frozen=True, slots=True)
class Mission:
    mission_id: str
    level: int
    title: str
    briefing: str
    objectives: tuple[MissionObjective, ...]
    detection_limit: float
    time_limit: float

    @property
    def target_node_id(self) -> str:
        return self.objectives[0].node_id

    @property
    def target_infection(self) -> float:
        return self.objectives[0].infection


@dataclass(frozen=True, slots=True)
class MissionResult:
    status: str
    reason: str
    score: int
    duration: float
    total_infection: float
    detection: float
    moves: int
    scans: int
    infections: int
    hides: int
