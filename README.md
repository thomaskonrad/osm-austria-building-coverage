# OpenStreetMap Austria Building Coverage

This is a services that continuously calculates the building outline coverage in OpenStreetMap compared to the Austrian
[basemap](http://www.basemap.at) for each Austrian municipality, district, and federal state.

[See The Site in Action!](https://osm-austria-building-coverage.thomaskonrad.at/)

# Basic Setup

Here is a rough outline of the setup process if you want to run the service on your own.

 * Install Python 3
 * Install required Python modules
    * `psycopg2`
    * `Pillow`
    * `numpy`
    * `cv2`
    * `requests`
 * Install PostgreSQL 9.x
 * Install required PostgreSQL extensions
    * PostGIS
    * `hstore`
 * Install other required software
    * `osm2pgsql`
    * `osmupdate`
    * `mb-util`
    * TileMill
 * Set up basic tiles
    * Download basempap Tiles at zoom level 16 (`scripts/basemap/basemap-tile-downloader.py`)
    * Extract buildings from basemap tiles (`scripts/basemap/basemap-extract-buildings.py`)
 * Import OSM Austria extract with `osm2pgsql`
 * Generate admin boundaries and tile indices per municipality
    * Create boundary database table (`scripts/coverage-scores/create-admin-boundaries.sql`)
    * Create new TileMill project with a PostgreSQL layer and the following statement `(select id, name, way, color as colorvalue from austria_admin_boundaries where admin_level=3) as municipalities`
    * Execute the script `scripts/coverage-scores/municipalities-cartocss.py` and paste the result into style.mss in TileMill
    * Render the result with the bounding box set to Austria any with zoom level 16 only (takes up about 200 MB of disk space)
    * Extract the tiles with `mb-util austria-municipalities.mbtiles austria-municipalities-16`
 * Prepare basemap buildings-only tiles for rendering them on a map
    * `scripts/mapnik/scale-tiles-to-lower-zoom-levels.py <path-to-basemap-buildings-only-tiles>/ 16`
 * Create a cronjob for the `update-all.sh` script and pass it the required arguments