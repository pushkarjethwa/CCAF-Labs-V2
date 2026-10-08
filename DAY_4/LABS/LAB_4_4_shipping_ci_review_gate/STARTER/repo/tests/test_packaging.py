from shipcalc import packaging


def test_dim_weight_cm():
    assert packaging.dim_weight_kg((50, 40, 25), 5000) == 10.0


def test_billable_is_max():
    assert packaging.billable_weight_kg(2.0, (50, 40, 25), 5000) == 10.0
    assert packaging.billable_weight_kg(12.0, (50, 40, 25), 5000) == 12.0
