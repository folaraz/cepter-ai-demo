"""A metric as passed out of total, with the IDs of the items that failed."""

from dataclasses import dataclass, field


@dataclass
class Ratio:
    passed: int = 0
    total: int = 0
    failures: list[str] = field(default_factory=list)

    def add(self, ok: bool, label: str) -> None:
        self.total += 1
        self.passed += ok
        if not ok:
            self.failures.append(label)

    @property
    def value(self) -> float | None:
        return self.passed / self.total if self.total else None
