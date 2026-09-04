from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from veneto_city_data.api.routes import get_city_service
from veneto_city_data.main import app
from veneto_city_data.models import City, Demographics, Economics, SourceMetadata


def city(name: str = "Padova", code: str = "028001", population: int = 70_000) -> City:
    source = SourceMetadata(
        organization="ISTAT",
        url="https://example.test/POSAS_2026.zip",
        reference_year=2026,
        retrieved_at=datetime(2026, 1, 2, tzinfo=UTC),
        stale=False,
    )
    return City(
        istat_code=code,
        name=name,
        province="Padova",
        demographics=Demographics(
            population=population,
            males=34_000,
            females=36_000,
            age_0_17=10_000,
            age_18_64=40_000,
            age_65_plus=20_000,
            average_age=45.1,
            source=source,
        ),
        economics=Economics(
            taxpayers=50_000,
            total_declared_income_eur=Decimal("1500000000"),
            average_income_per_taxpayer_eur=Decimal("30000.00"),
            total_net_tax_eur=Decimal("250000000"),
            source=source.model_copy(update={"organization": "MEF", "reference_year": 2024}),
        ),
    )


class FakeService:
    minimum_population = 50_000

    async def list_cities(self) -> list[City]:
        return [city(), city("Verona", "023091", 250_000)]


def client() -> TestClient:
    app.dependency_overrides[get_city_service] = FakeService
    return TestClient(app)


def test_health() -> None:
    assert client().get("/health").json() == {"status": "ok"}


def test_list_cities_supports_sorting() -> None:
    response = client().get("/api/v1/cities?sort=population&direction=desc")

    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert [item["name"] for item in response.json()["cities"]] == ["Verona", "Padova"]


def test_city_detail_and_not_found() -> None:
    api = client()

    assert api.get("/api/v1/cities/028001").json()["name"] == "Padova"
    assert api.get("/api/v1/cities/000000").status_code == 404


def test_csv_export() -> None:
    response = client().get("/api/v1/cities/export.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "istat_code,name,province" in response.text
    assert "028001,Padova,Padova" in response.text
