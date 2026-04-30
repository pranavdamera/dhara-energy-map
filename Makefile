PYTHON ?= python3
DEFAULT_DB_URL ?= postgresql://dhara_user:dhara_pass@localhost:5433/dhara

install:
	$(PYTHON) -m pip install -r backend/requirements.txt

db-up:
	docker compose up -d

db-down:
	docker compose down

init-db:
	psql "$${DATABASE_URL:-$(DEFAULT_DB_URL)}" -f scripts/00_init_db.sql

load-boundary:
	$(PYTHON) scripts/01_load_boundary.py

make-grid:
	$(PYTHON) scripts/02_make_candidate_grid.py

load-osm:
	$(PYTHON) scripts/04_load_osm.py

gee-export:
	$(PYTHON) scripts/05_gee_export_anantapur.py

zonal-stats:
	$(PYTHON) scripts/06_raster_to_zone_stats.py

compute-scores:
	$(PYTHON) scripts/07_compute_scores.py

smoke-test:
	$(PYTHON) scripts/08_smoke_test_db.py

smoke-api:
	PYTHONPATH=. $(PYTHON) scripts/09_smoke_api.py

seed-demo:
	PYTHONPATH=. $(PYTHON) scripts/seed_demo.py

api:
	uvicorn backend.app.main:app --reload --port 8000
