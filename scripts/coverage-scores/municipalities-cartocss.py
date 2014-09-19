#!/usr/bin/env python2

import psycopg2
import sys

# This script reads all municipalities from the database and outputs the corresponding CartoCSS (TileMill) style for
# indivually coloring each municipality.

# Try to connect
if len(sys.argv) < 4 or len(sys.argv) > 5:
    print "Usage: ./municipalities-cartocss.py <hostname> <dbname> <user> [<password>] " \
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
    cur.execute('SELECT id, color from austria_admin_boundaries where admin_level=3')
except:
    print "I can't SELECT from bar"

rows = cur.fetchall()
for row in rows:
    print "[id=%s] {polygon-fill: %s}" % (row[0], row[1])