from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass
from decimal import Decimal

from veneto_city_data.cache import CachedPayload, FileCache


@dataclass(frozen=True, slots=True)
class IncomeRecord:
    istat_code: str
    taxpayers: int | None
    total_declared_income_eur: Decimal | None
    average_income_per_taxpayer_eur: Decimal | None
    total_net_tax_eur: Decimal | None


class MefClient:
    def __init__(self, cache: FileCache, url: str) -> None:
        self.cache = cache
        self.url = url

    async def fetch(self) -> tuple[dict[str, IncomeRecord], CachedPayload]:
        payload = await self.cache.get("mef-income", self.url)
        return parse_mef_zip(payload.data), payload


def parse_mef_zip(data: bytes) -> dict[str, IncomeRecord]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        filename = next(name for name in archive.namelist() if name.lower().endswith(".csv"))
        text = io.TextIOWrapper(archive.open(filename), encoding="utf-8-sig", newline="")
        rows = csv.DictReader(text, delimiter=";")
        result: dict[str, IncomeRecord] = {}
        for row in rows:
            if row["Regione"].casefold() != "veneto":
                continue
            taxpayers = _optional_int(row["Numero contribuenti"])
            total_income = _optional_decimal(row["Reddito complessivo - Ammontare in euro"])
            average_income = (
                (total_income / taxpayers).quantize(Decimal("0.01"))
                if total_income is not None and taxpayers
                else None
            )
            code = row["Codice Istat Comune"].zfill(6)
            result[code] = IncomeRecord(
                istat_code=code,
                taxpayers=taxpayers,
                total_declared_income_eur=total_income,
                average_income_per_taxpayer_eur=average_income,
                total_net_tax_eur=_optional_decimal(row["Imposta netta - Ammontare in euro"]),
            )
    return result


def _optional_int(value: str) -> int | None:
    stripped = value.strip()
    return int(stripped) if stripped else None


def _optional_decimal(value: str) -> Decimal | None:
    stripped = value.strip()
    return Decimal(stripped) if stripped else None
