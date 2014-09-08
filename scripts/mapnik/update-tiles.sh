#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/"
date_string=`date +%Y-%m-%d`

function current_time()
{
	date +%Y-%m-%d_%H:%M:%S
}

log_file=~/logs/update-tiles-$(current_time).log
exec >  >(tee -a $log_file)
exec 2> >(tee -a $log_file >&2)

echo "$(current_time) Starting with OSM Austria Building Coverage tile update"

tiles_root_dir=$1
tiles_dir_base_name="osm-buildings-only"
tiles_sub_dir="$tiles_dir_base_name-$date_string"
tiles_dir=${tiles_root_dir}${tiles_sub_dir}
zoom_level=16

echo "$(current_time) Deleting existing directory..."
rm -rf $tiles_dir

echo "$(current_time) Generating tiles..."
${DIR}generate_tiles_multiprocess.py ${DIR}osm-buildings-only.xml $tiles_dir $zoom_level $zoom_level > /dev/null

if [ $? -eq 0 ]; then
    echo "$(current_time) Syncing highest zoom level with current tiles..."
    rsync -vrtc ${tiles_dir}/${zoom_level} ${tiles_root_dir}${tiles_dir_base_name}-current/${zoom_level}
    echo "$(current_time) Done!"

	echo "$(current_time) Scaling tiles to lower zoom levels..."
	${DIR}scale-tiles-to-lower-zoom-levels.py ${tiles_root_dir}${tiles_dir_base_name}-current/ $zoom_level > /dev/null

	if [ $? -eq 0 ]; then
		echo "$(current_time) Scaling tiles done."
	else
		echo "$(current_time) Scaling tiles failed."
	fi
else
	echo "$(current_time) Rendering tiles failed."
fi
