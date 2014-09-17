import psycopg2
import sys
import Image
import os
import struct
import datetime


def hex2rgb(hex):
    # Remove the hash in the beginning
    hex = hex[1:]
    return struct.unpack("BBB", hex.decode("hex"))


def main():
    if len(sys.argv) < 7 or len(sys.argv) > 8:
        print "Usage: ./update-coverage.py <municipality-tiles-path> <basemap-tiles-path> " \
              "<osm-tiles-path> <hostname> <dbname> <user> [<password>] # Paths with trailing slashes please. " \
              "The DB password is optional. If none is given, we'll try to connect without a password."
        sys.exit(1)

    muticipality_tiles_path = sys.argv[1]
    basemap_tiles_path = sys.argv[2]
    osm_tiles_path = sys.argv[3]

    for path in [muticipality_tiles_path, basemap_tiles_path, osm_tiles_path]:
        if not os.path.isdir(path):
            print "Path %s does not exist. Please specify a valid path." % (path)

    # Try to connect
    try:
        if len(sys.argv) == 7:
            conn = psycopg2.connect(
                host=sys.argv[4],
                database=sys.argv[5],
                user=sys.argv[6]
            )
        elif len(sys.argv) == 8:
            conn = psycopg2.connect(
                host=sys.argv[4],
                database=sys.argv[5],
                user=sys.argv[6],
                password=sys.argv[7]
            )
    except Exception as e:
        print "I am unable to connect to the database (%s)." % e.message
        sys.exit(1)

    cur = conn.cursor()

    try:
        cur.execute("SELECT id, name, full_tiles, partial_tiles, color "
                    "from austria_admin_boundaries "
                    "where admin_level=3")
    except:
        print "I can't SELECT!"
        sys.exit(1)

    rows = cur.fetchall()
    total = len(rows)
    processed = 0

    for municipality in rows:
        id = municipality[0]
        name = municipality[1]
        full_tiles = municipality[2]
        partial_tiles = municipality[3]
        color = municipality[4]

        cur.execute("select id, municipality_id, timestamp"
                    "from austria_building_coverage "
                    "where municipality_id=%d" % id)

        rows = cur.fetchall()

