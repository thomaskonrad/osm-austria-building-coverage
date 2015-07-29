#!/bin/bash

function current_time()
{
	date +%Y-%m-%d_%H:%M:%S
}

if [ "$#" -ne 4 ]; then
    echo "Usage: ./update-all.sh <log-directory> <db-working-directory> <tiles-root-directory> <database-name>"
    exit 1
fi

log_directory=$1
log_file=${log_directory}update-all.log
exec >  >(tee -a ${log_file})
exec 2> >(tee -a ${log_file} >&2)

echo "$(current_time) Starting update of OSM Austria database, building coverage tiles and coverage statistics"

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/"
db_working_directory=$2
tiles_root_directory=$3
database_name=$4

municipality_tiles_path=${tiles_root_directory}municipalities-colored/
basemap_tiles_path=${tiles_root_directory}basemap-buildings-extracted/
osm_tiles_path=${tiles_root_directory}osm-buildings-only-current/

echo "$(current_time) Incremental database update: Starting."
${scriptdir}osm-db-update/osm-update-austria-incremental.sh ${db_working_directory}
exit_code=$?
echo "$(current_time) Incremental database update: Process finished with exit code ${exit_code}."


if [ ${exit_code} -eq 0 ]; then
    echo "$(current_time) Incremental tile update and scaling: Starting."
    ${scriptdir}mapnik/update-tiles.sh ${tiles_root_directory}
    exit_code=$?
    echo "$(current_time) Incremental tile update and scaling: Process finished with exit code ${exit_code}."

    if [ ${exit_code} -eq 0 ]; then
        echo "$(current_time) Incremental coverage scores update: Starting."
        ${scriptdir}coverage-scores/update-coverage.py ${municipality_tiles_path} ${basemap_tiles_path} ${osm_tiles_path} ${database_name}
        exit_code=$?
        echo "$(current_time) Incremental coverage scores update: Process finished with exit code ${exit_code}."

        # Refresh the coverage score views
        echo "$(current_time) Refreshing materialized views..."
        ${scriptdir}coverage-scores/refresh-materialized-views.py ${database_name}
        exit_code=$?
        echo "$(current_time) Refresh materialized views: Process finished with exit code ${exit_code}."
    fi
fi
