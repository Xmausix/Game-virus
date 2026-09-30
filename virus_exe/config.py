from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SYSTEM_PATH = DATA_DIR / "systems.json"
MISSION_PATH = DATA_DIR / "missions.json"
DATABASE_PATH = DATA_DIR / "virus.sqlite3"
CUSTOM_DSL_PATH = DATA_DIR / "custom_virus.dsl"
WINDOW_SIZE = (1280, 760)
FPS = 60
GAME_TITLE = "Virus.exe"
