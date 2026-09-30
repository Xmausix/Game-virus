# Virus.exe

Grywalne MVP strategii puzzle stealth wykonane w Pythonie. Gracz steruje procesem wirusa w fikcyjnym systemie operacyjnym utrzymanym w stylu ultra retro CRT.

## Technologie

- Pygame — interfejs, graf systemu i główna pętla gry
- Matplotlib — wykres detekcji na ekranie końcowym
- FastAPI — API wyników i leaderboardu
- SQLite — trwały zapis sesji
- JSON — konfiguracja mapy i kampanii

## Kampania wielopoziomowa

1. FIRST CONTACT — Browser
2. QUIET EXPANSION — Browser i Mail
3. DATA HEIST — Browser, Mail i Files
4. RED ALERT — Security
5. SYSTEM CONTROL — wszystkie moduły

Po ukończeniu poziomu naciśnij `N`, aby przejść dalej. `R` uruchamia ponownie aktualny poziom.

## Uruchomienie

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m virus_exe
```

Na Windows:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
python -m virus_exe
```

## Sterowanie

- `S` lub przycisk `SCAN`
- `I` lub przycisk `INFECT`
- `H` lub przycisk `HIDE`
- `M` lub przycisk `MOVE`
- klikniecie wezla wybiera cel
- `N` przechodzi na nastepny poziom po zwyciestwie
- `R` restartuje aktualny poziom

Aby zainfekowac modul:

```text
wybierz modul -> MOVE -> INFECT
```

Tryb ultra retro zawiera:

- palete phosphor green, amber i red
- font monospace bez antyaliasingu
- scanlines CRT
- ramke monitora
- glitch bars
- ostre pikselowe panele
- statusy terminalowe

## API

W drugim terminalu:

```bash
python -m virus_exe.api
```

Dostepne endpointy:

- `GET /health`
- `GET /api/leaderboard?limit=20`
- `GET /api/stats`
- `GET /api/sessions/{id}`
- `POST /api/sessions`
- `GET /docs`

Baza SQLite jest tworzona automatycznie w `data/virus.sqlite3`.

## Struktura

```text
virus_exe/
├── analytics/
├── core/
├── game/
├── missions/
├── security/
├── storage/
├── ui/
└── virus/
data/
├── missions.json
└── systems.json
```
