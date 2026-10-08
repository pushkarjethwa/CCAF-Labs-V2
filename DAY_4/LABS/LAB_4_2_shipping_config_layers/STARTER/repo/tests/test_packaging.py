from shipcalc import packaging


def test_dimensional_weight_wins_for_a_light_big_box():
    assert packaging.billable_weight_kg(1.0, (50, 50, 50), 5000) == 25.0


def test_actual_weight_wins_for_a_dense_box():
    assert packaging.billable_weight_kg(8.0, (10, 10, 10), 5000) == 8.0
