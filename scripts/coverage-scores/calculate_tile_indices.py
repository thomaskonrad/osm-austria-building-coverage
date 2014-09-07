import psycopg2
import math
import re
import sys


def deg2num(lat_deg, lon_deg, zoom=16):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return xtile, ytile


def main():
    if len(sys.argv) < 4 or len(sys.argv) > 5:
        print "Usage: ./calculate_tile-indices.py <hostname> <dbname> <user> [<password>] " \
              "# The DB password is optional. If none is given, we'll try to connect without a password."
        sys.exit(1)

    # Try to connect
    try:
        if len(sys.argv) == 4:
            conn = psycopg2.connect(
                host=sys.argv[1],
                database=sys.argv[2],
                user=sys.argv[3]
            )
        elif len(sys.argv) == 5:
            conn = psycopg2.connect(
                host=sys.argv[1],
                database=sys.argv[2],
                user=sys.argv[3],
                password=sys.argv[4]
            )
    except Exception as e:
        print "I am unable to connect to the database (%s)." % e.message
        sys.exit(1)

    cur = conn.cursor()

    try:
        cur.execute("SELECT id, name, ST_AsEWKT(ST_Transform(bbox, 4326)), color from austria_admin_boundaries")
    except:
        print "I can't SELECT!"

    rows = cur.fetchall()
    for row in rows:
        id = row[0]
        name = row[1]
        bbox_raw = row[2]
        color = row[3]

        bbox = row[2]
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

            try:
                cur = conn.cursor()
                cur.execute("update austria_admin_boundaries "
                            "set tile_min_x_16=%d, tile_max_x_16=%d, "
                            "tile_min_y_16=%d, tile_max_y_16=%d "
                            "where id=%d" % (minx, maxx, miny, maxy, id))

                print "Tile ranges for %s (ID %s) inserted: %d %d / %d %d" % (name, id, minx, miny, maxx, maxy)
            except Exception as e:
                print "Municipality %s (ID %s) could not be processed, DB error (%s)." % (name, id, e.message)

        else:
            print "Municipality %s (ID %s) could not be processed, no bbox found." % (name, id)

    conn.commit()


if __name__ == "__main__":main()