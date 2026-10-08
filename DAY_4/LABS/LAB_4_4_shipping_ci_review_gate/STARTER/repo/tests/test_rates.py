import pytest

from shipcalc import rates


def test_bands_and_zone():
    assert rates.price_cents(0.5, 1) == 500
    assert rates.price_cents(4.9, 2) == 1035
    assert rates.price_cents(20.0, 1) == 2200


def test_too_heavy():
    with pytest.raises(ValueError):
        rates.price_cents(71, 1)
