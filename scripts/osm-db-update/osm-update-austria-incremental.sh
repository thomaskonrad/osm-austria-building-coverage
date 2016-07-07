#!/bin/bash

# The working directory
working_directory=$1

function current_time()
{
        date +%Y-%m-%d_%H:%M:%S
}

base_url='http://download.geofabrik.de/europe/austria-updates/'
file_name=${working_directory}austria-latest.osm.pbf
change_file_name=${working_directory}austria-updates.osm.osc
new_file_name=${working_directory}austria-latest-new.osm.pbf

echo "$(current_time) ### STARTING OSM AUSTRIA INCREMENTAL UPDATE"

osmupdate ${file_name} ${change_file_name} -v --base-url=http://download.geofabrik.de/europe/austria-updates/ --tempfiles="/tmp/osmupdate_temp"

osmupdate_status=$?

if [ ${osmupdate_status} -eq 0 ]; then
	echo "$(current_time) Creation of change file succeeded, importing data..."
	osm2pgsql -C4096 --number-processes 4 --append -s -S /usr/share/osm2pgsql/default.style ${change_file_name}

	if [ $? -eq 0 ]; then
		echo "$(current_time) Incremental update done. Moving files..."

		osmconvert ${file_name} ${change_file_name} -o=${new_file_name}

		rm -f ${file_name}
		mv ${new_file_name} ${file_name}
		rm -f ${change_file_name}

		echo "$(current_time) All done."
	else
		echo "$(current_time) Error while importing."
		exit 1
	fi
elif [ ${osmupdate_status} -eq 21 ]; then
	echo "$(current_time) Database is already up to date. Quitting."
	exit 21
else
	echo "$(current_time) Something went wrong wile updating."
	exit 1
fi
