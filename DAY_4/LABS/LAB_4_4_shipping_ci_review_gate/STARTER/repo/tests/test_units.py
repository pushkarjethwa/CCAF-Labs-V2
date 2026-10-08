from shipcalc import units


def test_lb_to_kg():
    assert abs(units.lb_to_kg(10) - 4.5359237) < 1e-9


def test_in_to_cm():
    assert units.in_to_cm(10) == 25.4
