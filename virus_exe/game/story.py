from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Dialogue:
    speaker: str
    text: str
    accent: str


DIALOGUES: tuple[Dialogue, ...] = (
    Dialogue("UNKNOWN", "Jesli to widzisz, system testowy nadal dziala.", "GREEN"),
    Dialogue("UNKNOWN", "Nie jestesmy w prawdziwej sieci. To zamkniete laboratorium.", "CYAN"),
    Dialogue("HANDLER", "Twoim zadaniem nie jest niszczenie. Masz znalezc bezpieczna sciezke.", "YELLOW"),
    Dialogue("HANDLER", "Kazdy krok zostawia slad, a kazdy slad zmienia zachowanie obrony.", "YELLOW"),
    Dialogue("VIRUS.EXE", "Zbuduj narzedzie, poznaj mape i zdecyduj, kiedy nie atakowac.", "GREEN"),
    Dialogue("SYSTEM", "Sesja gotowa. Otworz guide w dowolnym momencie.", "CYAN"),
)


@dataclass(slots=True)
class StoryState:
    index: int = 0

    @property
    def current(self) -> Dialogue | None:
        return DIALOGUES[self.index] if self.index < len(DIALOGUES) else None

    @property
    def finished(self) -> bool:
        return self.index >= len(DIALOGUES)

    def advance(self) -> None:
        self.index += 1
