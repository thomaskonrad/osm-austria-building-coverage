#!/usr/bin/env python3
import sys
import os
import requests
import time
import random

server = "http://maps%d.wien.gv.at"
zoomLevel = 16

minX = 34366
maxX = 35897
minY = 22496
maxY = 23220

numberOfRequests = 0
pauseAfterRequests = 1000
pauseInSeconds = 1

totalNumberOfTiles = (maxX - minX + 1) * (maxY - minY + 1)
numberOfTilesProcessed = 0

print("That's %d tiles total." % (totalNumberOfTiles))

# Loop through all tiles
for x in range(minX, maxX + 1):
    for y in range(minY, maxY + 1):
        directory = "basemap/%d/%d/" % (zoomLevel, x)
        file = directory + "%d.png" % (y)

        if not os.path.isfile(file):
            numberOfRequests += 1

            query = "/basemap/geolandbasemap/normal/google3857/%d/%d/%d.png" % (zoomLevel, y, x)

            # Issue the GET request
            randomServer = server % (random.randint(1, 4))
            print("Issuing request " + randomServer + query + "...")
            try:
                r = requests.get(randomServer + query)
            except requests.exceptions.ConnectionError:
                print("ConnectionError thrown. Waiting one minute...")
                # Wait a minute
                time.sleep(60)
                r = requests.get(randomServer + query)

            # Create the directories if they don't exist
            if not os.path.exists(directory):
                os.makedirs(directory)

            if r.status_code == requests.codes.ok:
                print("%d %d was found. Saving file." % (x, y))

                with open(file, 'wb') as fd:
                    for chunk in r.iter_content(1024):
                        fd.write(chunk)
            elif r.status_code == requests.codes.not_found:
                print("%d %d could not be found (HTTP 404). Creating empty file." % (x, y))
                open(file, 'a').close()
            else:
                print("HTTP error %d occurred while downloading %d %d." % (r.status_code, x, y))

            if numberOfRequests >= pauseAfterRequests:
                time.sleep(pauseInSeconds)
                numberOfRequests = 0
        else:
            print("Tile %d %d already exists." % (x, y))

        numberOfTilesProcessed += 1
        percent = numberOfTilesProcessed / totalNumberOfTiles * 100
        print(" --- Processed %d / %d (%.3f percent)" % (numberOfTilesProcessed, totalNumberOfTiles, percent))
