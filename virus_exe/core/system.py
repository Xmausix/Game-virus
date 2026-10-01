import json
from pathlib import Path

from virus_exe.core.models import Connection, Node, SystemGraph


def load_system(path: Path) -> SystemGraph:
    payload = json.loads(path.read_text(encoding="utf-8"))
    nodes = {
        item["id"]: Node(
            node_id=item["id"],
            name=item["name"],
            short_name=item["short_name"],
            x=item["x"],
            y=item["y"],
            security=item["security"],
            value=item["value"],
            category=item["category"],
            vulnerability=item.get("vulnerability", max(5, 100 - item["security"])),
            processes=tuple(item.get("processes", [])),
            user_activity=item.get("user_activity", 0),
        )
        for item in payload["nodes"]
    }
    connections = [Connection(**item) for item in payload["connections"]]
    return SystemGraph(name=payload["name"], nodes=nodes, connections=connections)
