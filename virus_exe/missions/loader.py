import json
from pathlib import Path

from virus_exe.missions.model import Mission, MissionObjective


def load_missions(path: Path) -> list[Mission]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    missions = []
    for index, item in enumerate(payload, start=1):
        raw_objectives = item.get("objectives") or [
            {"node": item["target_node"], "infection": item["target_infection"]}
        ]
        objectives = tuple(
            MissionObjective(node_id=objective["node"], infection=objective["infection"])
            for objective in raw_objectives
        )
        missions.append(
            Mission(
                mission_id=item["id"],
                level=item.get("level", index),
                title=item["title"],
                briefing=item["briefing"],
                objectives=objectives,
                detection_limit=item["detection_limit"],
                time_limit=item.get("time_limit", 0),
            )
        )
    return missions
