from dataclasses import dataclass, field


@dataclass(slots=True)
class Node:
    node_id: str
    name: str
    short_name: str
    x: int
    y: int
    security: int
    value: int
    category: str
    infection: float = 0.0
    detection: float = 0.0
    discovered: bool = False
    isolated: bool = False

    def add_infection(self, amount: float) -> None:
        self.infection = min(100.0, self.infection + amount)
        self.detection = min(100.0, self.detection + amount * 0.22)


@dataclass(frozen=True, slots=True)
class Connection:
    source: str
    target: str
    firewall: int = 0


@dataclass(slots=True)
class SystemGraph:
    name: str
    nodes: dict[str, Node]
    connections: list[Connection]
    _adjacency: dict[str, set[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._adjacency = {node_id: set() for node_id in self.nodes}
        for connection in self.connections:
            self._adjacency[connection.source].add(connection.target)
            self._adjacency[connection.target].add(connection.source)

    def get_node(self, node_id: str) -> Node:
        return self.nodes[node_id]

    def neighbors(self, node_id: str) -> set[str]:
        return self._adjacency.get(node_id, set())

    def is_connected(self, source: str, target: str) -> bool:
        return target in self._adjacency.get(source, set())

    def connection_between(self, source: str, target: str) -> Connection | None:
        for connection in self.connections:
            if {connection.source, connection.target} == {source, target}:
                return connection
        return None

    def total_infection(self) -> float:
        non_core = [node for node in self.nodes.values() if node.node_id != "core"]
        if not non_core:
            return 0.0
        return sum(node.infection for node in non_core) / len(non_core)
