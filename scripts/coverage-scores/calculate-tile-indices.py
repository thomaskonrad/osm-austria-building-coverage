import psycopg2
import math
import re
import sys
import os
import struct
import Image


def deg2num(lat_deg, lon_deg, zoom=16):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return xtile, ytile


def hex2rgb(hex):
    # Remove the hash in the beginning
    hex = hex[1:]
    return struct.unpack("BBB", hex.decode("hex"))


def main():
    if len(sys.argv) < 5 or len(sys.argv) > 6:
        print "Usage: ./calculate_tile-indices.py <municipality tiles path including trailing slash>  <hostname> " \
              "<dbname> <user> [<password>] # The DB password is optional. If none is given, we'll try to  connect " \
              "without a password."
        sys.exit(1)

    zoom_level = 16
    tile_path = sys.argv[1] + "%d/" % zoom_level

    if not os.path.exists(tile_path):
        print "The municipality tiles path given does not exist."
        sys.exit(1)

    tile_size = 256
    insert_statement_file = "calculate-tile-indices-inserts.sql"

    # Try to connect
    try:
        if len(sys.argv) == 5:
            conn = psycopg2.connect(
                host=sys.argv[2],
                database=sys.argv[3],
                user=sys.argv[4]
            )
        elif len(sys.argv) == 6:
            conn = psycopg2.connect(
                host=sys.argv[2],
                database=sys.argv[3],
                user=sys.argv[4],
                password=sys.argv[5]
            )
    except Exception as e:
        print "I am unable to connect to the database (%s)." % e.message
        sys.exit(1)

    cur = conn.cursor()

    try:
        cur.execute("SELECT id, name, ST_AsEWKT(ST_Transform(bbox, 4326)), color "
                    "from austria_admin_boundaries "
                    "where admin_level=3 "
                    "and (full_tiles is null or partial_tiles is null)")
    except:
        print "I can't SELECT!"

    rows = cur.fetchall()
    total = len(rows)
    processed = 0

    for municipality in rows:
        id = municipality[0]
        name = municipality[1]
        bbox = municipality[2]
        color = municipality[3]

        processed += 1
        percent = float(processed) / float(total) * float(100)
        print "Processing municipality %s (%d of %d, %.2f percent)." % (name, processed, total, percent)

        data = {
            'name': name,
            'full_tiles': [],
            'partial_tiles': []
        }

        m = re.search("\(\((.+?)\)\)", bbox)

        if m:
            bbox = m.group(1)
            coords = bbox.split(',')

            bbox_bottomleft = coords[0]
            bbox_topright = coords[2]

            bbox_bottomleft_x = float(bbox_bottomleft.split(' ')[0])
            bbox_bottomleft_y = float(bbox_bottomleft.split(' ')[1])
            bbox_topright_x   = float(bbox_topright.split(' ')[0])
            bbox_topright_y   = float(bbox_topright.split(' ')[1])

            (minx, maxy) = deg2num(bbox_bottomleft_y, bbox_bottomleft_x)
            (maxx, miny) = deg2num(bbox_topright_y, bbox_topright_x)

            # Loop through all tiles
            for x in range(minx, maxx + 1):
                for y in range(miny, maxy + 1):
                    current_tile_path = tile_path + "%d/%d.png" % (x, y)

                    if os.path.exists(current_tile_path):
                        municipality_tile = Image.open(current_tile_path).convert('RGB').load()
                        (mr, mg, mb) = hex2rgb(color)

                        contains_color = False
                        full_tile = True

                        for pixel_y in xrange(tile_size):
                            for pixel_x in xrange(tile_size):
                                (pr, pg, pb) = municipality_tile[pixel_x, pixel_y]

                                if mr == pr and mg == pg and mb == pb:
                                    contains_color = True
                                else:
                                    full_tile = False

                        if contains_color:
                            if full_tile:
                                data['full_tiles'].append([x, y])
                            else:
                                data['partial_tiles'].append([x, y])

            full_tiles_insert = "{" +\
                                ",".join("{%d,%d}" % (coords[0], coords[1]) for coords in data['full_tiles']) +\
                                "}"
            partial_tiles_insert = "{" +\
                                   ",".join("{%d,%d}" % (coords[0], coords[1]) for coords in data['partial_tiles']) +\
                                   "}"

            insert_statement = "update austria_admin_boundaries set full_tiles='%s', partial_tiles='%s' where id=%d " \
                               "and name='%s'"\
                               % (full_tiles_insert, partial_tiles_insert, id, name)

            with open(insert_statement_file, "a") as myfile:
                myfile.write(insert_statement + ";\n")

            cur.execute(insert_statement)
            conn.commit()

        else:
            print "Municipality %s (ID %s) could not be processed, no bbox found." % (name, id)


if __name__ == "__main__":main()