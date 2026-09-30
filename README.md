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

- `TAB` wlacza lub wylacza konsole
- `ENTER` wykonuje komende
- `BACKSPACE` usuwa znak
- `ESC` opuszcza konsole
- `S` lub przycisk `SCAN`
- `I` lub przycisk `INFECT`
- `H` lub przycisk `HIDE`
- `M` lub przycisk `MOVE`
- `A` lub przycisk `ATTACK`
- klikniecie wezla wybiera cel
- `N` przechodzi na nastepny poziom po zwyciestwie
- `R` restartuje aktualny poziom

## Konsola taktyczna

Gra posiada interaktywna konsole w stylu starego terminala. Przykladowa sekwencja:

```text
help
viruses
virus ghost
methods
method spoof
target browser
move
attack
status
```

Dostepne profile wirusow:

- `ghost` — wysoka skrytość i niski ślad
- `worm` — propagacja przez sieć
- `rootkit` — kontrola i persistence
- `locker` — wysoka moc i wysokie ryzyko

Dostepne metody ataku:

- `exploit` — mocny, ale glosny atak lokalny
- `phish` — atak modulow aktywnosci uzytkownika
- `lateral` — zdalny skok przez aktywne polaczenie
- `persist` — wymaga profilu `rootkit`
- `spoof` — mniejsza detekcja kosztem wolniejszej infekcji

Dzialanie metod uwzglednia:

- poziom bezpieczenstwa celu
- prawdopodobienstwo powodzenia
- czas wykonania
- CPU i network
- detekcje antywirusa
- kompatybilnosc wirusa z metoda
- aktywny cel skanowania

Aby wykonac atak lokalny:

```text
virus ghost
method exploit
target browser
move
attack
```

Metoda `lateral` moze zaatakowac sasiedni modul bez przemieszczania procesu:

```text
target mail
method lateral
attack
```

Mechaniki sa swiadomie abstrakcyjna symulacja w zamknietym fikcyjnym systemie. Gra nie wykonuje prawdziwych exploitow, nie laczy sie z siecia i nie modyfikuje systemu operacyjnego.

## Podjezyk Virus DSL

Edytor otwiera sie klawiszem `E`, gdy konsola nie jest aktywna. Mozna tez wpisac `editor` w konsoli.

```text
VIRUS CUSTOM_GHOST
POWER 62
STEALTH 86
SPREAD 48
PERSISTENCE 22
METHOD SPOOF
RULE DETECTION > 60 THEN HIDE
RULE SECURITY < 70 THEN ATTACK SPOOF
END
```

Obsluga edytora:

- `F5` uruchamia test
- `F6` laduje program do gry tylko gdy test zwroci `TRUE`
- `CTRL+S` zapisuje `data/custom_virus.dsl`
- `ESC` wraca do gry
- strzalki poruszaja kursorem

Test zawsze zwraca jednoznaczny wynik `TRUE` albo `FALSE`. Program nie przejdzie testu, gdy ma bledna skladnie, brak wymaganych pol, nieznana metode, wartosci poza zakresem albo zadna regula nie uruchamia sie w scenariuszu testowym.

Po zaladowaniu wlasnego wirusa:

```text
virus custom
auto
```

Komenda `auto` wlacza autopilota regul. Reguly moga reagowac na `DETECTION`, `SECURITY`, `CPU`, `NETWORK` i `INFECTION`, wykonujac `HIDE`, `MOVE`, `WAIT` albo `ATTACK`.

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
