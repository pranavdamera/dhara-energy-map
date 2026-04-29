from fastapi import FastAPI

from backend.app.routes.health import router as health_router
from backend.app.routes.sites import router as sites_router

app = FastAPI(title="Dhara Energy Map API", version="0.1.0")

app.include_router(health_router)
app.include_router(sites_router)


@app.get("/methodology")
def methodology():
    return {
        "scope": "Week 1 single-district demo for Anantapur only",
        "model": "Explainable weighted additive scoring",
        "weights": {
            "solar": 0.25,
            "substation": 0.20,
            "road": 0.15,
            "slope": 0.15,
            "land": 0.15,
            "crop": 0.10,
        },
        "crs": {
            "storage": "EPSG:4326",
            "metric": "EPSG:32644",
        },
    }
