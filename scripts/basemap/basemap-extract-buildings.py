#!/opt/local/bin/python2.7

import cv2
import Image
import numpy as np
import os
import sys

def morph(kernel, image, iterations = 1):
    for i in range(0, iterations):
        image = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
        image = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)

    return image

def extractBuildings(file):
    # Define colors
    startColor1 = np.array([174, 174, 217]) # 236, 202, 201
    endColor1 = np.array([213, 212, 255])
    startColor2 = np.array([152, 150, 206]) #171, 172, 230
    endColor2 = np.array([189, 180, 250])

    img = cv2.imread(file)
    color1 = cv2.inRange(img, startColor1, endColor1)
    color2 = cv2.inRange(img, startColor2, endColor2)
    combined = cv2.bitwise_or(color1, color2)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    combined = morph(kernel, combined)

    combined = cv2.bitwise_not(combined)
    image = Image.fromarray(combined)
    image.convert("RGBA")
    data = image.getdata()

    transparent = Image.new('RGBA', (256, 256))

    newData = []
    for item in data:
        if item == 255:
            newData.append((255, 255, 255, 0))
        else:
            newData.append((255, 0, 0, 255))

    transparent.putdata(newData)
    return transparent

def getTransparentImage(width = 256, height = 256):
    transparent = Image.new('RGBA', (256, 256))

    data = []
    for x in range(0, width):
        for y in range(0, height):
            data.append((255, 255, 255, 0))

    transparent.putdata(data)
    return transparent

def main():
    minX = int(sys.argv[1]) # 34366
    maxX = int(sys.argv[2]) # 35897
    minY = int(sys.argv[3]) # 22496
    maxY = int(sys.argv[4]) # 23220

    originalFilesPath = '../../basemap-tiles-16/%d/%d.jpeg'
    extractedFilesDirectory = '../../basemap-tiles-16-buildings-extracted/%d/'

    totalNumberOfTiles = (maxX - minX + 1) * (maxY - minY + 1)
    numberOfTilesProcessed = 0

    transparentImage = getTransparentImage(256, 256)

    # Loop through all tiles
    for x in range(minX, maxX + 1):
        # Create the current directory if it does not exist
        currentDirectory = extractedFilesDirectory % (x)
        if not os.path.exists(currentDirectory):
            os.makedirs(currentDirectory)

        for y in range(minY, maxY + 1):
            print("We're on %d / %d." % (x, y))
            original = originalFilesPath % (x, y)
            extracted = currentDirectory + "%d.png" % (y)

            if (os.path.exists(extracted)):
                print("File has already been processed. Skipping.")
            else:
                if os.path.isfile(original):
                    if os.path.getsize(original) > 0:
                        print("File exists and is not empty. Extracting buildings...")
                        extractedImage = extractBuildings(original)
                    else:
                        print("File exists but is empty. Creating transparent image...")
                        extractedImage = transparentImage

                    extractedImage.save(extracted)
                else:
                    print("Error: Tile %d / %d does not exist." % (x, y))

            numberOfTilesProcessed += 1
            percent = float(numberOfTilesProcessed) / float(totalNumberOfTiles) * float(100)
            print(" --- Processed %d / %d (%.3f percent)" % (numberOfTilesProcessed, totalNumberOfTiles, percent))


if __name__ == "__main__":main()