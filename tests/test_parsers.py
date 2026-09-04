from decimal import Decimal

from veneto_city_data.clients.istat import parse_istat_zip
from veneto_city_data.clients.mef import parse_mef_zip

from .helpers import istat_zip, mef_zip


def test_istat_parser_aggregates_ages_and_sexes() -> None:
    records = {record.istat_code: record for record in parse_istat_zip(istat_zip())}
    padova = records["028001"]

    assert padova.province == "Padova"
    assert padova.population == 70_000
    assert padova.males == 33_000
    assert padova.females == 37_000
    assert (padova.age_0_17, padova.age_18_64, padova.age_65_plus) == (19_000, 31_000, 20_000)
    assert padova.average_age == 26.54


def test_mef_parser_filters_veneto_and_calculates_average() -> None:
    records = parse_mef_zip(mef_zip())

    assert set(records) == {"028001"}
    assert records["028001"].total_declared_income_eur == Decimal("1500000000")
    assert records["028001"].average_income_per_taxpayer_eur == Decimal("30000.00")
