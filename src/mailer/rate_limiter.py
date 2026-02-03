import csv
import datetime as dt
from dataclasses import dataclass
from typing import Iterable


@dataclass
class RateLimiter:
    daily_limit: int
    min_seconds_between_sends: int

    def sent_today(self, log_rows: Iterable[dict]) -> int:
        today = dt.date.today().isoformat()
        count = 0
        for row in log_rows:
            timestamp = row.get("timestamp", "")
            if timestamp.startswith(today):
                count += 1
        return count

    def can_send(self, log_rows: Iterable[dict]) -> bool:
        return self.sent_today(log_rows) < self.daily_limit


def read_logs(path: str) -> list[dict]:
    try:
        with open(path, newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    except FileNotFoundError:
        return []
