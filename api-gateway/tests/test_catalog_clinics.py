from app.routers.clinics import _haversine_km
from app.services.catalog import PACKS, price_for


def test_pack_pricing_rub():
    amount, cur = price_for("mini", "RUB")
    assert amount == 149.0 and cur == "RUB"


def test_pack_pricing_uzs():
    amount, cur = price_for("main", "UZS")
    assert amount == 50000.0 and cur == "UZS"


def test_all_packs_have_expected_sizes():
    assert PACKS["mini"].generations_total == 5
    assert PACKS["main"].generations_total == 20
    assert PACKS["extended"].generations_total == 50


def test_haversine_moscow_spb():
    # Moscow (55.75, 37.62) -> Saint Petersburg (59.94, 30.31) ≈ 633 km
    d = _haversine_km(55.75, 37.62, 59.94, 30.31)
    assert 600 < d < 660
