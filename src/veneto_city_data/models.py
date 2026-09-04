from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class SortField(StrEnum):
    name = "name"
    population = "population"
    average_income = "average_income"


class SortDirection(StrEnum):
    asc = "asc"
    desc = "desc"


class SourceMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    organization: str
    url: str
    reference_year: int
    retrieved_at: datetime
    stale: bool


class Demographics(BaseModel):
    population: int
    males: int
    females: int
    age_0_17: int
    age_18_64: int
    age_65_plus: int
    average_age: float | None
    source: SourceMetadata


class Economics(BaseModel):
    taxpayers: int | None
    total_declared_income_eur: Decimal | None
    average_income_per_taxpayer_eur: Decimal | None
    total_net_tax_eur: Decimal | None
    source: SourceMetadata


class City(BaseModel):
    istat_code: str
    name: str
    province: str
    region: str = "Veneto"
    demographics: Demographics
    economics: Economics | None


class CityCollection(BaseModel):
    count: int
    minimum_population: int
    cities: list[City]


class HealthResponse(BaseModel):
    status: str
