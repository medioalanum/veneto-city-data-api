from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ISTAT_URL = "https://demo.istat.it/data/posas/POSAS_2026_en_All_files.zip"
DEFAULT_MEF_URL = (
    "https://www1.finanze.gov.it/finanze/analisi_stat/public/v_4_0_0/contenuti/"
    "Redditi_e_principali_variabili_IRPEF_su_base_comunale_CSV_2024.zip"
)


@dataclass(frozen=True, slots=True)
class Settings:
    cache_dir: Path = Path("data/cache")
    cache_ttl_seconds: int = 86_400
    request_timeout_seconds: float = 30.0
    minimum_population: int = 50_000
    istat_url: str = DEFAULT_ISTAT_URL
    mef_url: str = DEFAULT_MEF_URL

    @classmethod
    def from_environment(cls) -> Settings:
        return cls(
            cache_dir=Path(os.getenv("CACHE_DIR", "data/cache")),
            cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "86400")),
            request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
            minimum_population=int(os.getenv("MINIMUM_POPULATION", "50000")),
            istat_url=os.getenv("ISTAT_DATA_URL", DEFAULT_ISTAT_URL),
            mef_url=os.getenv("MEF_DATA_URL", DEFAULT_MEF_URL),
        )
