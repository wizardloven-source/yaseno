import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sqlalchemy import create_engine, text

engine = create_engine("postgresql://postgres:postgres@localhost:5432/erpya")
with engine.connect() as c:
    for t in ["fiscal_years", "fiscal_periods"]:
        try:
            r = c.execute(text(f"SELECT count(*) FROM {t}")).scalar()
            print(t, "->", r)
        except Exception as e:
            print(t, "-> ERROR:", e)
    try:
        rows = c.execute(text("SELECT id, name, is_closed, start_date, end_date FROM fiscal_periods LIMIT 5")).fetchall()
        for row in rows:
            print(row)
    except Exception as e:
        print("periods query error:", e)
    try:
        rows = c.execute(text("SELECT id, code, is_open FROM fiscal_years LIMIT 5")).fetchall()
        for row in rows:
            print("FY:", row)
    except Exception as e:
        print("years query error:", e)