from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VirusProfile:
    virus_id: str
    code_name: str
    description: str
    power: float
    stealth: float
    spread: float
    persistence: float
    detection_modifier: float


@dataclass(frozen=True, slots=True)
class AttackMethod:
    method_id: str
    label: str
    description: str
    base_success: float
    infection_gain: float
    duration: float
    noise: float
    cpu_cost: float
    network_cost: float
    remote: bool
    category: str | None = None
    required_virus: str | None = None


VIRUS_PROFILES: tuple[VirusProfile, ...] = (
    VirusProfile("ghost", "GHOST", "cichy implant zwiadowczy", 0.48, 0.90, 0.30, 0.18, 0.62),
    VirusProfile("worm", "WORM", "autonomiczny propagator sieciowy", 0.62, 0.42, 0.96, 0.30, 1.00),
    VirusProfile("rootkit", "ROOTKIT", "gleboki kontroler systemowy", 0.86, 0.58, 0.42, 1.00, 0.84),
    VirusProfile("locker", "LOCKER", "agresywny modol blokujacy", 1.00, 0.18, 0.25, 0.70, 1.40),
)


ATTACK_METHODS: tuple[AttackMethod, ...] = (
    AttackMethod("exploit", "EXPLOIT", "wykorzystuje abstrakcyjna luke modulu", 0.82, 42.0, 3.8, 10.0, 9.0, 3.0, False),
    AttackMethod("phish", "PHISH", "przejmuje modul aktywnosci uzytkownika", 0.78, 32.0, 4.5, 6.0, 6.0, 6.0, False, "user"),
    AttackMethod("lateral", "LATERAL", "przeskakuje przez aktywne polaczenie", 0.70, 30.0, 3.8, 12.0, 7.0, 12.0, True),
    AttackMethod("persist", "PERSIST", "instaluje fikcyjny wpis startowy", 0.64, 24.0, 5.0, 9.0, 10.0, 5.0, False, None, "rootkit"),
    AttackMethod("spoof", "SPOOF", "maskuje proces i obniza slad detekcji", 0.88, 18.0, 4.2, -6.0, 4.0, 2.0, False),
)


def virus_by_id(virus_id: str) -> VirusProfile | None:
    return next((profile for profile in VIRUS_PROFILES if profile.virus_id == virus_id), None)


def method_by_id(method_id: str) -> AttackMethod | None:
    return next((method for method in ATTACK_METHODS if method.method_id == method_id), None)
