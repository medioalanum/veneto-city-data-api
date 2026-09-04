from fastapi import FastAPI

from veneto_city_data import __version__
from veneto_city_data.api.routes import router

app = FastAPI(
    title="Veneto City Data API",
    version=__version__,
    description=(
        "Demographic and income indicators for Veneto municipalities with more than "
        "50,000 residents, sourced from ISTAT and the Italian Ministry of Economy and Finance."
    ),
)
app.include_router(router)
