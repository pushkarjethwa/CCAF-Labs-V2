import pytest

from shipcalc import rates


def test_zone_one_is_the_base_price():
    assert rates.price_cents(0.5, 1) == 500


def test_zone_three_adds_thirty_percent():
    assert rates.price_cents(10.0, 3) == 2860


def test_too_heavy_is_rejected():
    with pytest.raises(ValueError):
        rates.price_cents(80.0, 1)


def test_half_cent_tie_rounds_up():
    assert rates.price_cents(3.0, 2) == 863   # 750 * 1.15 = 862.5
