from bot.risk import kelly_fraction


def test_kelly_zero_on_bad_price():
    assert kelly_fraction(0.6, 0) == 0.0
    assert kelly_fraction(0.6, 1) == 0.0


def test_kelly_positive_edge():
    k = kelly_fraction(0.7, 0.4)
    assert k > 0
    assert abs(k - (0.3 / 0.6)) < 1e-9


def test_kelly_no_edge():
    assert kelly_fraction(0.4, 0.5) == 0.0
