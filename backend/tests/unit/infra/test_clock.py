from datetime import UTC, date, datetime

from app.core.clock import FixedClock, SystemClock


def test_fixed_clock_returns_the_fixed_moment():
    clock = FixedClock(datetime(2026, 11, 19, 10, 30, tzinfo=UTC))

    assert clock.now() == datetime(2026, 11, 19, 10, 30, tzinfo=UTC)
    assert clock.today() == date(2026, 11, 19)


def test_system_clock_is_timezone_aware():
    assert SystemClock().now().tzinfo is not None
