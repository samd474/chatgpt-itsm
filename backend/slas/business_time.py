"""Business-time arithmetic, independent of the ORM so it can be tested directly.

All arithmetic happens in UTC; business windows are interpreted in the calendar's
own time zone, so daylight-saving transitions are handled correctly.
"""
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

MAX_DAYS = 3660


@dataclass
class Schedule:
    tz: ZoneInfo
    # weekday (0 = Monday) -> list of (start, end) local times. Empty dict = 24x7.
    windows: dict[int, list[tuple[time, time]]] = field(default_factory=dict)
    holidays: set[date] = field(default_factory=set)

    @property
    def is_24x7(self):
        return not self.windows

    def windows_on(self, day):
        """UTC (start, end) pairs for one local calendar day."""
        if day in self.holidays:
            return []
        result = []
        for start, end in sorted(self.windows.get(day.weekday(), [])):
            local_start = datetime.combine(day, start, tzinfo=self.tz)
            local_end = datetime.combine(day, end, tzinfo=self.tz)
            result.append((local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc)))
        return result


def add_business_minutes(schedule, start, minutes):
    """Return the instant `minutes` business minutes after `start` (an aware datetime)."""
    if minutes < 0:
        raise ValueError("minutes must not be negative")
    start = start.astimezone(timezone.utc)
    if minutes == 0:
        return start
    if schedule.is_24x7 and not schedule.holidays:
        return start + timedelta(minutes=minutes)

    remaining = timedelta(minutes=minutes)
    cursor = start
    day = start.astimezone(schedule.tz).date()
    for _ in range(MAX_DAYS):
        windows = schedule.windows_on(day) if not schedule.is_24x7 else (
            [] if day in schedule.holidays else [(
                datetime.combine(day, time.min, tzinfo=schedule.tz).astimezone(timezone.utc),
                datetime.combine(day + timedelta(days=1), time.min, tzinfo=schedule.tz).astimezone(timezone.utc),
            )]
        )
        for window_start, window_end in windows:
            effective = max(window_start, cursor)
            if effective >= window_end:
                continue
            available = window_end - effective
            if remaining <= available:
                return effective + remaining
            remaining -= available
            cursor = window_end
        day += timedelta(days=1)
    raise ValueError("The calendar has no business hours within ten years")


def business_minutes_between(schedule, start, end):
    """Business minutes elapsed between two instants (0 if end <= start)."""
    start = start.astimezone(timezone.utc)
    end = end.astimezone(timezone.utc)
    if end <= start:
        return 0
    if schedule.is_24x7 and not schedule.holidays:
        return int((end - start).total_seconds() // 60)

    total = timedelta()
    day = start.astimezone(schedule.tz).date()
    last_day = end.astimezone(schedule.tz).date()
    while day <= last_day:
        if schedule.is_24x7:
            windows = [] if day in schedule.holidays else [(
                datetime.combine(day, time.min, tzinfo=schedule.tz).astimezone(timezone.utc),
                datetime.combine(day + timedelta(days=1), time.min, tzinfo=schedule.tz).astimezone(timezone.utc),
            )]
        else:
            windows = schedule.windows_on(day)
        for window_start, window_end in windows:
            overlap_start = max(window_start, start)
            overlap_end = min(window_end, end)
            if overlap_end > overlap_start:
                total += overlap_end - overlap_start
        day += timedelta(days=1)
    return int(total.total_seconds() // 60)
