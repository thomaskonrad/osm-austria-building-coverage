#!/usr/bin/env python3

import psycopg2
import sys
from PIL import Image
import os
import struct
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


def get_number_of_coverage_entries(cur, boundary_id):
    cur.execute("select count(*) from austria_building_coverage where boundary_id = %s", (boundary_id,))
    return cur.fetchone()[0]


def get_latest_coverage_entry(cur, boundary_id):
    cur.execute("""
                select c1.id as id, extract(epoch from c1.timestamp) as latest_timestamp,
                c1.covered_basemap_pixels, c1.total_basemap_pixels, c1.coverage
                from austria_building_coverage c1
                where boundary_id = %s
                and timestamp =
                    (select max(timestamp) from austria_building_coverage c2
                    where c2.boundary_id = c1.boundary_id)
                """,
                (boundary_id,))
    return cur.fetchone()


def update_coverage_entry_timestamp(cur, conn, entry_id, timestamp):
    cur.execute("update austria_building_coverage set timestamp = to_timestamp(%s) where id = %s",
                ("%.0f" % timestamp, entry_id,))
    conn.commit()


def update_coverage_high_level(cur, conn, boundaries_updated):
    # Record boundaries that have been updated
    boundaries_coverage_updated = []

    if len(boundaries_updated) > 0:
        cur.execute("""
                    select b.id
                    from austria_admin_boundaries b
                    left join austria_admin_boundaries m on (m.parent = b.id)
                    where m.id = ANY(%s)
                    group by b.id
                    """,
                    (boundaries_updated,))
        boundaries_to_update = cur.fetchall()

        for boundary in boundaries_to_update:
            boundary_id = boundary[0]

            number_of_entries = get_number_of_coverage_entries(cur, boundary_id)

            latest_entry = get_latest_coverage_entry(cur, boundary_id)

            cur.execute("""select extract(epoch from max(c.timestamp)), sum(c.covered_basemap_pixels), sum(c.total_basemap_pixels)
                        from austria_admin_boundaries parent
                        left join austria_admin_boundaries child on (child.parent = parent.id)
                        left join austria_building_coverage c on (c.boundary_id = child.id)
                        where c.timestamp = (select max(timestamp) from austria_building_coverage c2 where c.boundary_id = c2.boundary_id)
                        and parent.id = %s
                        """,
                        (boundary_id,))

            result = cur.fetchone()

            if result is not None and result[0] is not None:
                # Calculate district coverage and avoid division by zero
                if result[1] > 0:
                    boundary_coverage = result[1] / result[2] * 100.0
                else:
                    boundary_coverage = 0.0

                if latest_entry is None or result[1] != latest_entry[2] or result[2] != latest_entry[3]:
                    boundaries_coverage_updated.append(boundary_id)

                    print("Calculated coverage of boundary #%s (coverage: %.2f percent)." % (boundary_id, boundary_coverage))
                    cur.execute("insert into austria_building_coverage "
                            "(boundary_id, timestamp, covered_basemap_pixels, total_basemap_pixels, coverage) "
                            "values ("
                            "%s, to_timestamp(%s), %s, %s, %s"
                            ")",
                            (
                                boundary_id,
                                "%.0f" % result[0],
                                result[1],
                                result[2],
                                boundary_coverage,
                            )
                        )
                    conn.commit()
                elif number_of_entries > 1:
                    boundaries_coverage_updated.append(boundary_id)
                    update_coverage_entry_timestamp(cur, conn, latest_entry[0], result[0])
                else:
                    print("Boundary %d marked for update but not affected." % boundary_id)

            else:
                print("Error: No coverage results of boundary %d could be calculated." % boundary_id)

    return boundaries_coverage_updated


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
    parser.add_argument("-O", "--onlyhighlevel", action="store_true",
                        help="Set this if you want to update only the high-level boundaries (districts, federal states,"
                             "the whole country) from the current municipality coverage scores.")

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

    all_municipalities = cur.fetchall()
    print("%d municipalities found." % len(all_municipalities))

    if not args.onlyhighlevel:
        municipalities_coverage_updated = []

        for municipality in all_municipalities:
            id = municipality[0]
            name = municipality[1]
            full_tiles = municipality[2]
            partial_tiles = municipality[3]
            color = municipality[4]

            entry_count = get_number_of_coverage_entries(cur, id)

            latest_coverage_row = get_latest_coverage_entry(cur, id)

            latest_tile_timestamp = get_latest_timestamp(
                full_tiles + partial_tiles,
                [
                    basemap_tiles_path + schema,
                    osm_tiles_path + schema,
                ],
                zoom)

            if latest_coverage_row is None or latest_coverage_row[1] < latest_tile_timestamp:
                print("Municipality %s (ID %d) is out of date. Updating..." % (name, id))

                (covered_basemap_pixels_full, uncovered_basemap_pixels_full) = \
                    calculate_coverage_full_tiles(basemap_tiles_path, osm_tiles_path, zoom, schema, tile_size, full_tiles)

                (covered_basemap_pixels_partial, uncovered_basemap_pixels_partial) =\
                    calculate_coverage_partial_tiles(municipality_tiles_path, basemap_tiles_path, osm_tiles_path, color, zoom, schema, tile_size, partial_tiles)

                covered_basemap_pixels = covered_basemap_pixels_full + covered_basemap_pixels_partial
                uncovered_basemap_pixels = uncovered_basemap_pixels_full + uncovered_basemap_pixels_partial
                total_basemap_pixels = covered_basemap_pixels + uncovered_basemap_pixels

                # Calculate coverage and avoid a division by zero.
                if total_basemap_pixels > 0:
                    coverage = covered_basemap_pixels / total_basemap_pixels * 100.0
                else:
                    coverage = 0.0

                # Only insert the values if no entry exists yet or if the values have actually changed.
                if latest_coverage_row is None or latest_coverage_row[2] != covered_basemap_pixels or \
                    latest_coverage_row[3] != total_basemap_pixels:
                    municipalities_coverage_updated.append(id)

                    cur.execute("insert into austria_building_coverage "
                        "(boundary_id, timestamp, covered_basemap_pixels, total_basemap_pixels, coverage) "
                        "values ("
                        "%s, to_timestamp(%s), %s, %s, %s"
                        ")",
                        (
                            id,
                            "%.0f" % latest_tile_timestamp,
                            covered_basemap_pixels,
                            total_basemap_pixels,
                            coverage,
                        )
                    )
                    conn.commit()
                # We update the timestamp only if the entry count is higher than one. The problem is that if a tile is
                # updated that is part of the municipality's tile set but does not affect the municipality, the
                # timestamp of the last coverage is simply updated. That may lead to the case where some municipalities
                # do not have an austria_building_coverage entry on the first day.
                elif entry_count > 1:
                    print("The latest timestamp of the tiles of municipality %s has changed but these changes did not "
                          "affect this municipality. Only updating the timestsamp of entry %d." % (name, latest_coverage_row[0]))

                    municipalities_coverage_updated.append(id)
                    update_coverage_entry_timestamp(cur, conn, latest_coverage_row[0], latest_tile_timestamp)
                else:
                    print("The latest timestamp of the tiles of municipality %s has changed but these changes did not "
                          "affect this municipality. Not updating the timestamp anyway because the municipality has "
                          "only one coverage score entry. Updating the timestamp would cause the municipality not to "
                          "have a score entry on the first day." % name)


    # Alright, all municipalities updated. Now let's update the total coverage scores of districts, federal states and
    # the whole contry where necessary.

    if args.onlyhighlevel:
        municipalities_coverage_updated = []

        for municipality in all_municipalities:
            municipalities_coverage_updated.append(municipality[0])

    # Update districts.
    districts_updated = update_coverage_high_level(cur, conn, municipalities_coverage_updated)

    # Update federal states.
    states_updated = update_coverage_high_level(cur, conn, districts_updated)

    # Update the whole country.
    update_coverage_high_level(cur, conn, states_updated)


if __name__ == "__main__":
    main()
