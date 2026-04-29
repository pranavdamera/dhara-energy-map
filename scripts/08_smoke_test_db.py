import argparse
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://dhara_user:dhara_pass@localhost:5433/dhara")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-connection-only", action="store_true")
    args = parser.parse_args()

    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        print("DB connection: OK")
        if args.check_connection_only:
            return

        tables = ["districts", "candidate_sites", "roads", "substations", "scores"]
        for t in tables:
            cnt = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one()
            print(f"{t} count: {cnt}")

        top = conn.execute(
            text(
                """
                SELECT c.grid_id, s.total_score, s.confidence_score
                FROM scores s
                JOIN candidate_sites c ON c.id = s.site_id
                ORDER BY s.total_score DESC
                LIMIT 10;
                """
            )
        ).mappings().all()
        print("Top 10 scores:")
        for row in top:
            print(dict(row))


if __name__ == "__main__":
    main()
