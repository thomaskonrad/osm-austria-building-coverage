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

    try:
        cur.execute("REFRESH MATERIALIZED VIEW coverage_score_base")
        cur.execute("REFRESH MATERIALIZED VIEW coverage_boundary")
        conn.commit()
        
        print("Materialized views successfully updated.")
    except Exception as e:
        print("I can't SELECT! (%s)" % str(e))
        sys.exit(1)


if __name__ == "__main__":main()
