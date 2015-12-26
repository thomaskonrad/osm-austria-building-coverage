#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/"
date_string=`date +%Y-%m-%d`

function current_time()
{
	date +%Y-%m-%d_%H:%M:%S
}

echo "$(current_time) Starting with OSM Austria Building Coverage tile update"

tiles_root_dir=$1
tiles_dir_base_name="osm-buildings-only"
tiles_sub_dir="$tiles_dir_base_name-$date_string"
tiles_dir=${tiles_root_dir}${tiles_sub_dir}
zoom_level=16

echo "$(current_time) Deleting existing directory..."
rm -rf ${tiles_dir}

echo "$(current_time) Generating tiles..."
${DIR}generate_tiles_multiprocess.py ${DIR}osm-buildings-only.xml ${tiles_dir} ${zoom_level} ${zoom_level} > /dev/null

if [ $? -eq 0 ]; then
    # Create the target directory if it does not exist yet.
    mkdir -p ${tiles_root_dir}${tiles_dir_base_name}-current/${zoom_level}/

    echo "$(current_time) Syncing highest zoom level with current tiles..."
    rsync -vrc --stats ${tiles_dir}/${zoom_level}/ ${tiles_root_dir}${tiles_dir_base_name}-current/${zoom_level}/
    echo "$(current_time) Done!"

    # We remove the temporary tiles directory
    rm -r ${tiles_dir}

	echo "$(current_time) Scaling tiles to lower zoom levels..."
	${DIR}scale-tiles-to-lower-zoom-levels.py ${tiles_root_dir}${tiles_dir_base_name}-current/ ${zoom_level}

	if [ $? -eq 0 ]; then
		echo "$(current_time) Scaling tiles done."
	else
		echo "$(current_time) Scaling tiles failed."
		exit 1
	fi
else
	echo "$(current_time) Rendering tiles failed."
	exit 1
fi
