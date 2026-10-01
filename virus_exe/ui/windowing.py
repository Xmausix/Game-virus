from dataclasses import dataclass


@dataclass(slots=True)
class WindowState:
    app_id: str
    minimized: bool = False
    maximized: bool = False
    pinned: bool = False
