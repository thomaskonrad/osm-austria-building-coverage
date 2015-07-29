#!/usr/bin/env python3

import sys
import psycopg2


def main():
    if len(sys.argv) < 2:
        print("Usage: ./update-materialized-views.py <dbname>")
        sys.exit(1)

    # Try to connect
    try:
        conn = psycopg2.connect(
            database=sys.argv[1]
        )
    except Exception as e:
        print("I am unable to connect to the database (%s)." % e.message)
        sys.exit(1)

    cur = conn.cursor()

    statements = [
        "REFRESH MATERIALIZED VIEW coverage_boundary_base",
        "REFRESH MATERIALIZED VIEW coverage_boundary",
        "ALTER SEQUENCE coverage_score_id_seq RESTART WITH 1",
        "REFRESH MATERIALIZED VIEW coverage_score_base",
        "REFRESH MATERIALIZED VIEW coverage_change_date",
        "REFRESH MATERIALIZED VIEW coverage_score"
    ]

    for statement in statements:
        try:
            cur.execute(statement)
        except Exception as e:
            print("I can't SELECT (%s)! The statement causing the error was '%s'." % (str(e), statement))
            conn.rollback()
            conn.close()
            sys.exit(1)

    conn.commit()
    conn.close()
    print("Materialized views successfully updated.")


if __name__ == "__main__":
    main()
