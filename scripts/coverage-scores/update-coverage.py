#!/usr/bin/env python3

import psycopg2
import sys
from PIL import Image
import os
import struct
import math
import argparse
import math


def hex2rgb(hex):
    # Remove the hash in the beginning
    hex = hex[1:]
    return struct.unpack('BBB', bytes.fromhex(hex))


def calculate_coverage_full_tiles(basemap_tiles_path, osm_tiles_path, zoom, schema, tile_size, tile_indices):
    covered_basemap_pixels = 0
    uncovered_basemap_pixels = 0

    for index in tile_indices:
        x = index[0]
        y = index[1]

        basemap_tile_path = basemap_tiles_path + schema % (zoom, x, y)
        osm_tile_path = osm_tiles_path + schema % (zoom, x, y)

        basemap_tile = Image.open(basemap_tile_path).load()
        osm_tile = Image.open(osm_tile_path).convert('RGBA').load()

        for pixel_y in range(tile_size):
            for pixel_x in range(tile_size):
                (cbr, cbg, cbb, cba) = basemap_tile[pixel_x, pixel_y]
                (cor, cog, cob, coa) = osm_tile[pixel_x, pixel_y]

                if cba != 0: # basemap pixel
                    if coa != 0: # Also OSM pixel
                        covered_basemap_pixels += 1
                    else: # Only basemap pixel
                        uncovered_basemap_pixels += 1

    return covered_basemap_pixels, uncovered_basemap_pixels


def calculate_coverage_partial_tiles(municipality_tiles_path, basemap_tiles_path, osm_tiles_path, color, zoom, schema, tile_size, tile_indices):
    covered_basemap_pixels = 0
    uncovered_basemap_pixels = 0

    (r, g, b) = hex2rgb(color)

    for index in tile_indices:
        x = index[0]
        y = index[1]

        municipality_tile_path = municipality_tiles_path + schema % (zoom, x, y)
        basemap_tile_path = basemap_tiles_path + schema % (zoom, x, y)
        osm_tile_path = osm_tiles_path + schema % (zoom, x, y)

        municipality_tile = Image.open(municipality_tile_path).convert('RGBA').load()
        basemap_tile = Image.open(basemap_tile_path).load()
        osm_tile = Image.open(osm_tile_path).convert('RGBA').load()

        for pixel_y in range(tile_size):
            for pixel_x in range(tile_size):
                (cmr, cmg, cmb, cma) = municipality_tile[pixel_x, pixel_y]
                (cbr, cbg, cbb, cba) = basemap_tile[pixel_x, pixel_y]
                (cor, cog, cob, coa) = osm_tile[pixel_x, pixel_y]

                if cmr == r and cmg == g and cmb == b:
                    # We're on this municipality
                    if cba != 0: # basemap pixel
                        if coa != 0: # Also OSM pixel
                            covered_basemap_pixels += 1
                        else: # Only basemap pixel
                            uncovered_basemap_pixels += 1

    return covered_basemap_pixels, uncovered_basemap_pixels


def get_latest_timestamp(tile_indices, full_schemata, zoom):
    latest_timestamp = 0

    for full_schema in full_schemata:
        for index in tile_indices:
            x = index[0]
            y = index[1]

            tile_path = full_schema % (zoom, x, y)

            if os.path.exists(tile_path):
                timestamp = os.path.getmtime(tile_path)
                if timestamp > latest_timestamp:
                    latest_timestamp = timestamp
    
    # We only need seconds precision
    return math.floor(latest_timestamp)


def main():
    parser = argparse.ArgumentParser(description="Update the coverage scores of each outdated municipality.")

    parser.add_argument("-m", "--municipality-tiles-path", dest="municipality_tiles_path", required=True,
                        help="The path to the municipality tiles (with a trailing slash)")
    parser.add_argument("-b", "--basemap-tiles-path", dest="basemap_tiles_path", required=True,
                        help="The path to the basemap tiles (with a trailing slash)")
    parser.add_argument("-o", "--osm-tiles-path", dest="osm_tiles_path", required=True,
                        help="The path to the OSM tiles (with a trailing slash)")
    parser.add_argument("-H", "--hostname", dest="hostname", required=False, help="The database hostname")
    parser.add_argument("-d", "--database", dest="database", nargs='?', default="gis", help="The name of the database")
    parser.add_argument("-u", "--user", dest="user", required=False, help="The database user")
    parser.add_argument("-p", "--password", dest="password", required=False, help="The database password")

    args = parser.parse_args()

    municipality_tiles_path = os.path.expanduser(args.municipality_tiles_path)
    basemap_tiles_path = os.path.expanduser(args.basemap_tiles_path)
    osm_tiles_path = os.path.expanduser(args.osm_tiles_path)

    tile_size = 256
    zoom = 16
    schema = "%d/%d/%d.png"

    for path in [municipality_tiles_path, basemap_tiles_path, osm_tiles_path]:
        if not os.path.isdir(path):
            print("Path %s does not exist. Please specify a valid path." % (path))
            sys.exit(1)

    # Try to connect
    try:
        conn = psycopg2.connect(
            host=args.hostname,
            database=args.database,
            user=args.user,
            password=args.password
        )
    except Exception as e:
        print("I am unable to connect to the database (%s)." % str(e))
        sys.exit(1)

    cur = conn.cursor()

    try:
        cur.execute("SELECT id, name, full_tiles, partial_tiles, color "
                    "from austria_admin_boundaries "
                    "where admin_level=3")
    except Exception as e:
        print("I can't SELECT! (%s)" % str(e))
        sys.exit(1)

    rows = cur.fetchall()
    print("%d municipalities found." % len(rows))

    for municipality in rows:
        id = municipality[0]
        name = municipality[1]
        full_tiles = municipality[2]
        partial_tiles = municipality[3]
        color = municipality[4]

        cur.execute("select c1.id as id, extract(epoch from c1.timestamp) as latest_timestamp,"
                    "c1.covered_basemap_pixels, c1.total_basemap_pixels, c1.coverage "
                    "from austria_building_coverage c1 "
                    "where boundary_id = %d "
                    "and timestamp = "
                    "(select max(timestamp) from austria_building_coverage c2 "
                    "where c2.boundary_id = c1.boundary_id)" % id)
        coverage_rows = cur.fetchall()

        latest_tile_timestamp = get_latest_timestamp(
            full_tiles + partial_tiles,
            [
                basemap_tiles_path + schema,
                osm_tiles_path + schema,
            ],
            zoom)

        if len(coverage_rows) == 0 or coverage_rows[0][1] < latest_tile_timestamp:
            print("Municipality %s (ID %d) is out of date. Updating..." % (name, id))

            (covered_basemap_pixels_full, uncovered_basemap_pixels_full) = \
                calculate_coverage_full_tiles(basemap_tiles_path, osm_tiles_path, zoom, schema, tile_size, full_tiles)

            (covered_basemap_pixels_partial, uncovered_basemap_pixels_partial) =\
                calculate_coverage_partial_tiles(municipality_tiles_path, basemap_tiles_path, osm_tiles_path, color, zoom, schema, tile_size, partial_tiles)

            covered_basemap_pixels = covered_basemap_pixels_full + covered_basemap_pixels_partial
            uncovered_basemap_pixels = uncovered_basemap_pixels_full + uncovered_basemap_pixels_partial
            total_basemap_pixels = covered_basemap_pixels + uncovered_basemap_pixels

            coverage = covered_basemap_pixels / total_basemap_pixels * 100.0

            # Only insert the values if no entry exists yet or if the values have actually changed
            if len(coverage_rows) == 0 or coverage_rows[0][2] != covered_basemap_pixels or \
                coverage_rows[0][3] != total_basemap_pixels:
                cur.execute("insert into austria_building_coverage "
                    "(boundary_id, timestamp, covered_basemap_pixels, total_basemap_pixels, coverage) "
                    "values ("
                    "%d, to_timestamp(%.0f), %d, %d, %f"
                    ")" %
                    (
                        id,
                        latest_tile_timestamp,
                        covered_basemap_pixels,
                        total_basemap_pixels,
                        coverage
                    )
                )
                conn.commit()
            else:
                print("The latest timestamp of the tiles of municipality %s has changed but these changes did not " \
                      "affect this municipality. Only updating the timestsamp of entry %d." % (name, coverage_rows[0][0]))
                statement = "update austria_building_coverage set timestamp = to_timestamp(%.0f) " \
                            "where id = %d" % (latest_tile_timestamp, coverage_rows[0][0])
                cur.execute(statement)
                conn.commit()


if __name__ == "__main__":main()
