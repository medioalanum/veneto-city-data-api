from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass

from veneto_city_data.cache import CachedPayload, FileCache

VENETO_PROVINCES = {
    "023": "Verona",
    "024": "Vicenza",
    "025": "Belluno",
    "026": "Treviso",
    "027": "Venezia",
    "028": "Padova",
    "029": "Rovigo",
}


@dataclass(frozen=True, slots=True)
class PopulationRecord:
    istat_code: str
    name: str
    province: str
    population: int
    males: int
    females: int
    age_0_17: int
    age_18_64: int
    age_65_plus: int
    average_age: float | None


class IstatClient:
    def __init__(self, cache: FileCache, url: str) -> None:
        self.cache = cache
        self.url = url

    async def fetch(self) -> tuple[list[PopulationRecord], CachedPayload]:
        payload = await self.cache.get("istat-population", self.url)
        return parse_istat_zip(payload.data), payload


def parse_istat_zip(data: bytes) -> list[PopulationRecord]:
    aggregates: dict[str, dict[str, int | str]] = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        filenames = [
            name
            for name in archive.namelist()
            if name.lower().endswith(".csv") and _province_code(name) in VENETO_PROVINCES
        ]
        for filename in filenames:
            province_code = _province_code(filename)
            text = io.TextIOWrapper(archive.open(filename), encoding="utf-8-sig", newline="")
            next(text, None)  # Dataset title row.
            for row in csv.DictReader(text):
                if not row.get("Municipality code") or not row.get("Age"):
                    continue
                code = row["Municipality code"].zfill(6)
                age = _parse_age(row["Age"])
                if age == 999:  # Provider-supplied total; individual ages are aggregated below.
                    continue
                total = _integer(row["Total"])
                current = aggregates.setdefault(
                    code,
                    {
                        "name": row["Municipality"],
                        "province": VENETO_PROVINCES[province_code],
                        "population": 0,
                        "males": 0,
                        "females": 0,
                        "age_0_17": 0,
                        "age_18_64": 0,
                        "age_65_plus": 0,
                        "weighted_age": 0,
                    },
                )
                current["population"] = int(current["population"]) + total
                current["males"] = int(current["males"]) + _integer(row["Total males"])
                current["females"] = int(current["females"]) + _integer(row["Total females"])
                bucket = "age_0_17" if age <= 17 else "age_18_64" if age <= 64 else "age_65_plus"
                current[bucket] = int(current[bucket]) + total
                current["weighted_age"] = int(current["weighted_age"]) + age * total

    records = []
    for code, values in aggregates.items():
        population = int(values["population"])
        records.append(
            PopulationRecord(
                istat_code=code,
                name=str(values["name"]),
                province=str(values["province"]),
                population=population,
                males=int(values["males"]),
                females=int(values["females"]),
                age_0_17=int(values["age_0_17"]),
                age_18_64=int(values["age_18_64"]),
                age_65_plus=int(values["age_65_plus"]),
                average_age=round(int(values["weighted_age"]) / population, 2)
                if population
                else None,
            )
        )
    return records


def _province_code(filename: str) -> str:
    match = re.search(r"_(\d{3})_", filename)
    return match.group(1) if match else ""


def _parse_age(value: str) -> int:
    match = re.search(r"\d+", value)
    if not match:
        raise ValueError(f"Unsupported ISTAT age value: {value}")
    return int(match.group())


def _integer(value: str) -> int:
    return int(value.strip() or "0")
