import psycopg2
import sys
import Image
import os
import struct


def hex2rgb(hex):
    # Remove the hash in the beginning
    hex = hex[1:]
    return struct.unpack("BBB", hex.decode("hex"))


def calculate_coverage_full_tiles(basemap_tiles_path, osm_tiles_path, zoom, schema, tile_size, tile_indices):
    total_pixels = 0
    covered_basemap_pixels = 0
    uncovered_basemap_pixels = 0

    for index in tile_indices:
        x = index[0]
        y = index[1]

        basemap_tile_path = basemap_tiles_path + schema % (zoom, x, y)
        osm_tile_path = osm_tiles_path + schema % (zoom, x, y)

        basemap_tile = Image.open(basemap_tile_path).load()
        osm_tile = Image.open(osm_tile_path).convert('RGBA').load()

        for pixel_y in xrange(tile_size):
            for pixel_x in xrange(tile_size):
                total_pixels += 1
                (cbr, cbg, cbb, cba) = basemap_tile[pixel_x, pixel_y]
                (cor, cog, cob, coa) = osm_tile[pixel_x, pixel_y]

                if cba != 0: # basemap pixel
                    if coa != 0: # Also OSM pixel
                        covered_basemap_pixels += 1
                    else: # Only basemap pixel
                        uncovered_basemap_pixels += 1

    return total_pixels, covered_basemap_pixels, uncovered_basemap_pixels


def calculate_coverage_partial_tiles(municipality_tiles_path, basemap_tiles_path, osm_tiles_path, color, zoom, schema, tile_size, tile_indices):
    total_pixels = 0
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

        for pixel_y in xrange(tile_size):
            for pixel_x in xrange(tile_size):
                (cmr, cmg, cmb, cma) = municipality_tile[pixel_x, pixel_y]
                (cbr, cbg, cbb, cba) = basemap_tile[pixel_x, pixel_y]
                (cor, cog, cob, coa) = osm_tile[pixel_x, pixel_y]

                if cmr == r and cmg == g and cmb == b:
                    total_pixels += 1
                    # We're on this municipality
                    if cba != 0: # basemap pixel
                        if coa != 0: # Also OSM pixel
                            covered_basemap_pixels += 1
                        else: # Only basemap pixel
                            uncovered_basemap_pixels += 1

    return total_pixels, covered_basemap_pixels, uncovered_basemap_pixels


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
    return round(latest_timestamp)


def main():
    if len(sys.argv) < 7 or len(sys.argv) > 8:
        print "Usage: ./update-coverage.py <municipality-tiles-path> <basemap-tiles-path> <osm-tiles-path> " \
              "<hostname> <dbname> <user> [<password>] # Paths with trailing slashes please. The DB password is " \
              "optional. If none is given, we'll try to connect without a password."
        sys.exit(1)

    municipality_tiles_path = sys.argv[1]
    basemap_tiles_path = sys.argv[2]
    osm_tiles_path = sys.argv[3]
    tile_size = 256
    zoom = 16
    schema = "%d/%d/%d.png"

    for path in [municipality_tiles_path, basemap_tiles_path, osm_tiles_path]:
        if not os.path.isdir(path):
            print "Path %s does not exist. Please specify a valid path." % (path)

    # Try to connect
    try:
        if len(sys.argv) == 7:
            conn = psycopg2.connect(
                database=sys.argv[5],
                user=sys.argv[6],
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
    except Exception as e:
        print "I can't SELECT! (%s)" % str(e)
        sys.exit(1)

    rows = cur.fetchall()
    print "%d municipalities found." % len(rows)

    for municipality in rows:
        id = municipality[0]
        name = municipality[1]
        full_tiles = municipality[2]
        partial_tiles = municipality[3]
        color = municipality[4]

        cur.execute("select c1.id, extract(epoch from c1.timestamp), c1.covered_basemap_pixels, "
                    "c1.uncovered_basemap_pixels "
                    "from austria_building_coverage c1 "
                    "where municipality_id = %d "
                    "and timestamp = "
                    "(select max(timestamp) from austria_building_coverage c2 "
                    "where c2.municipality_id = c1.municipality_id)" % id)
        coverage_rows = cur.fetchall()

        latest_timestamp = get_latest_timestamp(
            full_tiles + partial_tiles,
            [
                basemap_tiles_path + schema,
                osm_tiles_path + schema,
            ],
            zoom)

        if len(coverage_rows) == 0 or coverage_rows[0][1] < latest_timestamp:
            print "Municipality %s (ID %d) is out of date. Updating..." % (name, id)

            (total_pixels_full, covered_basemap_pixels_full, uncovered_basemap_pixels_full) = \
                calculate_coverage_full_tiles(basemap_tiles_path, osm_tiles_path, zoom, schema, tile_size, full_tiles)

            (total_pixels_partial, covered_basemap_pixels_partial, uncovered_basemap_pixels_partial) =\
                calculate_coverage_partial_tiles(municipality_tiles_path, basemap_tiles_path, osm_tiles_path, color, zoom, schema, tile_size, partial_tiles)

            covered_basemap_pixels = covered_basemap_pixels_full + covered_basemap_pixels_partial
            uncovered_basemap_pixels = uncovered_basemap_pixels_full + uncovered_basemap_pixels_partial
            total_pixels = total_pixels_partial + total_pixels_full

            # Only insert the values if no entry exists yet or if the values have actually changed
            if len(coverage_rows) == 0 or coverage_rows[0][2] != covered_basemap_pixels or coverage_rows[0][3] != uncovered_basemap_pixels:
                cur.execute("insert into austria_building_coverage "
                    "(municipality_id, timestamp, total_pixels, covered_basemap_pixels, uncovered_basemap_pixels) "
                    "values ("
                    "%d, to_timestamp(%.0f), %d, %d, %d"
                    ")" %
                    (
                        id,
                        latest_timestamp,
                        total_pixels,
                        covered_basemap_pixels,
                        uncovered_basemap_pixels
                    )
                )
                conn.commit()
            else:
                print "The latest timestamp of the tiles of municipality %s has changed but these changes did not " \
                      "affect this municipality. Only updating the timestsamp of entry %d." % (name, coverage_rows[0][0])
                statement = "update austria_building_coverage set timestamp = to_timestamp(%.0f) " \
                            "where id = %d" % (latest_timestamp, coverage_rows[0][0])
                cur.execute(statement)
                conn.commit()


if __name__ == "__main__":main()
