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
        print "Usage: ./calculate_current_coverage.py <municipality-tiles-path> <basemap-tiles-path> " \
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

    cur = conn.cursor()
    data = {}

    tile_size = 256
    zoom = 16
    schema = "%d/%d/%d.png"

    startx = 34503
    endx = 35892
    starty = 22500
    endy = 23217

    today = str(datetime.date.today())

    total_number_of_tiles = (endx - startx + 1) * (endy - starty + 1)
    number_of_tiles_processed = 0

    # Loop through all tiles
    for x in range(startx, endx + 1):
        for y in range(starty, endy + 1):
            municipality_tile_path = muticipality_tiles_path + schema % (zoom, x, y)

            if os.path.exists(municipality_tile_path):
                basemap_tile_path = basemap_tiles_path + schema % (zoom, x, y)
                osm_tile_path = osm_tiles_path + schema % (zoom, x, y)

                municipality_tile = Image.open(municipality_tile_path).convert('RGBA').load()
                basemap_tile = Image.open(basemap_tile_path).load()
                osm_tile = Image.open(osm_tile_path).convert('RGBA').load()

                cur.execute("select b.id, b.name, b.color, c.timestamp "
                            "from austria_admin_boundaries, austria_building_coverage c "
                            "where c.municipality_id = b.id and "
                            "admin_level = 3 and "
                            "tile_min_x_16 <= %d and "
                            "tile_max_x_16 >= %d and "
                            "tile_min_y_16 <= %d and "
                            "tile_max_y_16 >= %d" % (x, x, y, y))

                rows = cur.fetchall()

                if len(rows) > 0:
                    current_municipalities = []

                    for row in rows:
                        current_municipalities.append({
                            'id': int(row[0]),
                            'name': row[1],
                            'color': hex2rgb(row[2]),
                            'total_pixels': 0,
                            'covered_basemap_pixels': 0,
                            'uncovered_basemap_pixels': 0
                        })

                    for pixel_y in xrange(tile_size):
                        for pixel_x in xrange(tile_size):
                            (cmr, cmg, cmb, cma) = municipality_tile[pixel_x, pixel_y]
                            (cbr, cbg, cbb, cba) = basemap_tile[pixel_x, pixel_y]
                            (cor, cog, cob, coa) = osm_tile[pixel_x, pixel_y]

                            for municipality in current_municipalities:
                                (r, g, b) = municipality['color']

                                if cmr == r and cmg == g and cmb == b:
                                    # We're on this municipality
                                    municipality['total_pixels'] += 1

                                    if cba != 0: # basemap pixel
                                        if coa != 0: # Also OSM pixel
                                            municipality['covered_basemap_pixels'] += 1
                                        else: # Only basemap pixel
                                            municipality['uncovered_basemap_pixels'] += 1

                    for municipality in current_municipalities:
                        if municipality['id'] in data:
                            # The municipality is already in the final dataset. Update numbers.
                            data[municipality['id']]['total_pixels'] += municipality['total_pixels']
                            data[municipality['id']]['covered_basemap_pixels'] += municipality['covered_basemap_pixels']
                            data[municipality['id']]['uncovered_basemap_pixels'] += municipality['uncovered_basemap_pixels']
                        else:
                            # The municipality is not yet in the final dataset. Create it.
                            data[municipality['id']] = {
                                'name': municipality['name'],
                                'total_pixels': municipality['total_pixels'],
                                'covered_basemap_pixels': municipality['covered_basemap_pixels'],
                                'uncovered_basemap_pixels': municipality['uncovered_basemap_pixels']
                            }

            number_of_tiles_processed += 1
            percent = float(number_of_tiles_processed) / float(total_number_of_tiles) * float(100)
            print(" --- Processed %d / %d (%.3f percent)" % (number_of_tiles_processed, total_number_of_tiles, percent))

    print "Writing changes into the database..."
    for key in data:
        entry = data[key]
        cur.execute("insert into austria_building_coverage "
                    "(municipality_id, capture_date, total_pixels, covered_basemap_pixels, uncovered_basemap_pixels) "
                    "values ("
                    "%d, '%s', %d, %d, %d"
                    ")" %
                    (
                        key,
                        today,
                        entry['total_pixels'],
                        entry['covered_basemap_pixels'],
                        entry['uncovered_basemap_pixels']
                    )
        )
        conn.commit()

    print "Done."


if __name__ == "__main__":main()