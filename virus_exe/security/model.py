from dataclasses import dataclass


@dataclass(slots=True)
class SecurityState:
    detection: float = 0.0
    antivirus_enabled: bool = True
    scan_elapsed: float = 0.0
    scan_duration: float = 9.0
    scan_index: int = 0
    warning_level: str = "QUIET"

    def update_warning(self) -> None:
        if self.detection < 30:
            self.warning_level = "QUIET"
        elif self.detection < 50:
            self.warning_level = "WARNING"
        elif self.detection < 70:
            self.warning_level = "ACTIVE SCAN"
        elif self.detection < 90:
            self.warning_level = "ISOLATION"
        else:
            self.warning_level = "PURGING"

    def add_detection(self, amount: float) -> None:
        self.detection = min(100.0, self.detection + max(0.0, amount))
        self.update_warning()

    def reduce_detection(self, amount: float) -> None:
        self.detection = max(0.0, self.detection - max(0.0, amount))
        self.update_warning()
