from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
SYSTEM_PATH = DATA_DIR / "systems.json"
MISSION_PATH = DATA_DIR / "missions.json"
DATABASE_PATH = DATA_DIR / "virus.sqlite3"
CUSTOM_DSL_PATH = DATA_DIR / "custom_virus.dsl"
SETTINGS_PATH = DATA_DIR / "settings.json"
SAVE_PATH = DATA_DIR / "savegame.json"
SAVE_DIR = DATA_DIR / "saves"
MAX_SAVE_SLOTS = 3
WINDOW_SIZE = (1280, 760)
FPS = 60
GAME_TITLE = "Virus.exe"
