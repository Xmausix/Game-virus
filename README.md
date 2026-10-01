# Virus.exe

Grywalne MVP strategii puzzle stealth wykonane w Pythonie. Gracz steruje procesem wirusa w fikcyjnym systemie operacyjnym utrzymanym w stylu ultra retro CRT.

## Technologie

- Pygame — interfejs, graf systemu i główna pętla gry
- Matplotlib — wykres detekcji na ekranie końcowym
- FastAPI — API wyników i leaderboardu
- SQLite — trwały zapis sesji
- JSON — konfiguracja mapy i kampanii

## Uruchomienie

Projekt korzysta z `pygame-ce`, który zachowuje import `pygame` i posiada gotowe wheels dla Python 3.10–3.14.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m virus_exe
```

Na Windows:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m virus_exe
```

Jeżeli wcześniej utworzono środowisko z nieudaną instalacją `pygame`, najlepiej usunąć je i utworzyć ponownie:

```powershell
Remove-Item -Recurse -Force .venv
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Sterowanie

- `TAB` lub `C` otwiera okno konsoli
- `ENTER` wykonuje komende
- `BACKSPACE` usuwa znak
- `ESC` zamyka aktywne okno lub wraca do menu
- `E` lub `F2` otwiera okno edytora kodu
- `G` lub `F1` otwiera okno guide
- `T` otwiera zadania, `V` Virus Lab, `H` sklep, `R` zlecenia, `F` pliki, `O` ustawienia
- w guide `LEFT/RIGHT` zmieniaja strone
- `F10` wykonuje `SAVE & EXIT`
- `S` lub przycisk `SCAN`
- `Q` lub przycisk `ANALYZE`
- `I` lub przycisk `INFECT`
- `H` lub przycisk `HIDE`
- `M` lub przycisk `MOVE`
- `A` lub przycisk `ATTACK`
- klikniecie wezla wybiera cel
- `N` przechodzi na nastepny poziom po zwyciestwie
- `R` restartuje aktualny poziom

