from __future__ import annotations

import asyncio
import re
from decimal import Decimal

from veneto_city_data.clients.istat import IstatClient
from veneto_city_data.clients.mef import MefClient
from veneto_city_data.models import City, Demographics, Economics, SourceMetadata


class CityService:
    def __init__(self, istat: IstatClient, mef: MefClient, minimum_population: int) -> None:
        self.istat = istat
        self.mef = mef
        self.minimum_population = minimum_population

    async def list_cities(self) -> list[City]:
        (population_records, istat_payload), (income_records, mef_payload) = await asyncio.gather(
            self.istat.fetch(), self.mef.fetch()
        )
        istat_year = _year_from_url(self.istat.url)
        mef_year = _year_from_url(self.mef.url)
        cities = []
        for population in population_records:
            if population.population <= self.minimum_population:
                continue
            income = income_records.get(population.istat_code)
            economics = None
            if income:
                economics = Economics(
                    taxpayers=income.taxpayers,
                    total_declared_income_eur=income.total_declared_income_eur,
                    average_income_per_taxpayer_eur=income.average_income_per_taxpayer_eur,
                    total_net_tax_eur=income.total_net_tax_eur,
                    source=SourceMetadata(
                        organization="MEF — Dipartimento delle Finanze",
                        url=self.mef.url,
                        reference_year=mef_year,
                        retrieved_at=mef_payload.retrieved_at,
                        stale=mef_payload.stale,
                    ),
                )
            cities.append(
                City(
                    istat_code=population.istat_code,
                    name=population.name,
                    province=population.province,
                    demographics=Demographics(
                        population=population.population,
                        males=population.males,
                        females=population.females,
                        age_0_17=population.age_0_17,
                        age_18_64=population.age_18_64,
                        age_65_plus=population.age_65_plus,
                        average_age=population.average_age,
                        source=SourceMetadata(
                            organization="ISTAT",
                            url=self.istat.url,
                            reference_year=istat_year,
                            retrieved_at=istat_payload.retrieved_at,
                            stale=istat_payload.stale,
                        ),
                    ),
                    economics=economics,
                )
            )
        return cities


def sort_cities(cities: list[City], field: str, descending: bool) -> list[City]:
    def key(city: City) -> str | int | Decimal:
        if field == "population":
            return city.demographics.population
        if field == "average_income":
            if city.economics and city.economics.average_income_per_taxpayer_eur is not None:
                return city.economics.average_income_per_taxpayer_eur
            return Decimal("-1")
        return city.name.casefold()

    return sorted(cities, key=key, reverse=descending)


def _year_from_url(url: str) -> int:
    years = re.findall(r"(?:19|20)\d{2}", url)
    if not years:
        raise ValueError(f"The source URL does not contain a reference year: {url}")
    return int(years[-1])
