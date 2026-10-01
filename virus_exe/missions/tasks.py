import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    title: str
    description: str
    hint: str
    condition: str
    reward: int
    tier: int


@dataclass(slots=True)
class TaskManager:
    tasks: tuple[Task, ...] = field(default_factory=tuple)
    current_index: int = 0
    completed: set[str] = field(default_factory=set)
    hint_used: set[str] = field(default_factory=set)
    reputation: int = 0
    xp: int = 0
    level: int = 1

    def __post_init__(self) -> None:
        if not self.tasks:
            self.tasks = load_tasks()

    @property
    def current(self) -> Task | None:
        return self.tasks[self.current_index] if self.current_index < len(self.tasks) else None

    @property
    def all_complete(self) -> bool:
        return self.current_index >= len(self.tasks)

    def hint(self) -> str:
        task = self.current
        if task is None:
            return "BRAK AKTYWNEGO ZADANIA"
        if task.task_id in self.hint_used:
            return "PODPOWIEDZ DLA TEGO ZADANIA ZOSTALA JUZ UZYWANA"
        self.hint_used.add(task.task_id)
        return task.hint

    def update(self, state) -> Task | None:
        task = self.current
        if task is None or not self._condition_met(task.condition, state):
            return None
        self.completed.add(task.task_id)
        self.current_index += 1
        self.reputation += task.reward
        self.xp += task.reward
        self.level = 1 + self.xp // 100
        return task

    def _condition_met(self, condition: str, state) -> bool:
        if condition.startswith("event:"):
            return condition[6:] in state.event_flags
        if condition.startswith("file:"):
            return state.vfs.exists(condition[5:])
        if condition.startswith("code:"):
            return condition[5:] in state.code_checks
        if condition.startswith("shop:"):
            return condition[5:] in state.shop_purchases
        if condition.startswith("infection:"):
            node_id, required = condition[11:].split(">=", 1)
            return state.graph.get_node(node_id).infection >= float(required)
        if condition.startswith("reputation>="):
            return self.reputation >= int(condition[12:])
        if condition.startswith("level>="):
            return self.level >= int(condition[7:])
        return False


def load_tasks() -> tuple[Task, ...]:
    path = Path(__file__).resolve().parents[2] / "data" / "tasks.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return tuple(Task(**item) for item in payload)
