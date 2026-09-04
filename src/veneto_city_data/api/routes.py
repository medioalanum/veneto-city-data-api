from __future__ import annotations

import csv
import io
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from veneto_city_data.cache import FileCache, SourceUnavailableError
from veneto_city_data.clients.istat import IstatClient
from veneto_city_data.clients.mef import MefClient
from veneto_city_data.config import Settings
from veneto_city_data.models import (
    City,
    CityCollection,
    HealthResponse,
    SortDirection,
    SortField,
)
from veneto_city_data.services.cities import CityService, sort_cities

router = APIRouter()


@lru_cache
def get_settings() -> Settings:
    return Settings.from_environment()


@lru_cache
def get_city_service() -> CityService:
    settings = get_settings()
    cache = FileCache(
        settings.cache_dir, settings.cache_ttl_seconds, settings.request_timeout_seconds
    )
    return CityService(
        IstatClient(cache, settings.istat_url),
        MefClient(cache, settings.mef_url),
        settings.minimum_population,
    )


CityServiceDependency = Annotated[CityService, Depends(get_city_service)]


@router.get("/health", response_model=HealthResponse, tags=["Operations"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/api/v1/cities", response_model=CityCollection, tags=["Cities"])
async def list_cities(
    service: CityServiceDependency,
    sort: SortField = SortField.name,
    direction: SortDirection = SortDirection.asc,
) -> CityCollection:
    cities = await _load_cities(service)
    ordered = sort_cities(cities, sort.value, direction is SortDirection.desc)
    return CityCollection(
        count=len(ordered), minimum_population=service.minimum_population, cities=ordered
    )


@router.get("/api/v1/cities/export.csv", response_class=Response, tags=["Cities"])
async def export_cities(
    service: CityServiceDependency,
    sort: SortField = SortField.name,
    direction: SortDirection = SortDirection.asc,
) -> Response:
    cities = sort_cities(await _load_cities(service), sort.value, direction is SortDirection.desc)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=_CSV_FIELDS)
    writer.writeheader()
    for city in cities:
        writer.writerow(_flatten_city(city))
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="veneto-cities.csv"'},
    )


@router.get("/api/v1/cities/{istat_code}", response_model=City, tags=["Cities"])
async def get_city(
    istat_code: str,
    service: CityServiceDependency,
) -> City:
    cities = await _load_cities(service)
    city = next((item for item in cities if item.istat_code == istat_code), None)
    if city is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found")
    return city


async def _load_cities(service: CityService) -> list[City]:
    try:
        return await service.list_cities()
    except SourceUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error


_CSV_FIELDS = [
    "istat_code",
    "name",
    "province",
    "region",
    "population",
    "males",
    "females",
    "age_0_17",
    "age_18_64",
    "age_65_plus",
    "average_age",
    "population_reference_year",
    "taxpayers",
    "total_declared_income_eur",
    "average_income_per_taxpayer_eur",
    "total_net_tax_eur",
    "income_reference_year",
]


def _flatten_city(city: City) -> dict[str, object]:
    economics = city.economics
    return {
        "istat_code": city.istat_code,
        "name": city.name,
        "province": city.province,
        "region": city.region,
        "population": city.demographics.population,
        "males": city.demographics.males,
        "females": city.demographics.females,
        "age_0_17": city.demographics.age_0_17,
        "age_18_64": city.demographics.age_18_64,
        "age_65_plus": city.demographics.age_65_plus,
        "average_age": city.demographics.average_age,
        "population_reference_year": city.demographics.source.reference_year,
        "taxpayers": economics.taxpayers if economics else None,
        "total_declared_income_eur": economics.total_declared_income_eur if economics else None,
        "average_income_per_taxpayer_eur": (
            economics.average_income_per_taxpayer_eur if economics else None
        ),
        "total_net_tax_eur": economics.total_net_tax_eur if economics else None,
        "income_reference_year": economics.source.reference_year if economics else None,
    }
