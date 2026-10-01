import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    fullscreen: bool = True
    resolution: str = "1280x760"
    subtitles: bool = True
    font_name: str = "DejaVu Sans Mono"
    font_size: int = 11
    high_contrast: bool = False
    reduce_motion: bool = False

    @classmethod
    def load(cls, path: Path) -> "Settings":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            allowed = {field: data[field] for field in asdict(cls()).keys() if field in data}
            settings = cls(**allowed)
            if settings.resolution not in settings.resolutions():
                settings.resolution = cls().resolution
            return settings
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    def resolutions(self) -> tuple[str, ...]:
        return ("1280x760", "1366x768", "1600x900")

    def resolution_size(self) -> tuple[int, int]:
        width, height = self.resolution.split("x", 1)
        return int(width), int(height)

    def cycle_resolution(self, amount: int = 1) -> None:
        values = self.resolutions()
        index = values.index(self.resolution) if self.resolution in values else 0
        self.resolution = values[(index + amount) % len(values)]

    def cycle_font(self) -> None:
        fonts = ["DejaVu Sans Mono", "Liberation Mono", "Consolas"]
        index = fonts.index(self.font_name) if self.font_name in fonts else 0
        self.font_name = fonts[(index + 1) % len(fonts)]

    def change_size(self, amount: int) -> None:
        self.font_size = max(9, min(16, self.font_size + amount))
