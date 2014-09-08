#!/usr/bin/env python2

import sys
import os
import Image


def get_transparent_image(width=256, height=256):
    transparent = Image.new('RGBA', (256, 256))

    data = []
    for x in range(0, width):
        for y in range(0, height):
            data.append((255, 255, 255, 0))

    transparent.putdata(data)
    return transparent


def get_image_or_transparent(path, width=256, height=256):
    if os.path.exists(path):
        return Image.open(path)
    else:
        return get_transparent_image(width, height)


def is_file_newer_than(file1, file2):
    if os.path.exists(file1) and os.path.exists(file2):
        return os.path.getctime(file1) > os.path.getctime(file2)

    if not os.path.exists(file1):
        return False


def main():
    if len(sys.argv) < 3:
        print "Usage: ./scale-tiles-to-lower-zoom-levels.py <tiles_path> <starting_zoom_level>"
        sys.exit(1)

    starting_zoom_level = int(sys.argv[2])

    lowestZoomLevel = 6
    highestZoomLevel = starting_zoom_level - 1
    minX = 34366
    maxX = 35897
    minY = 22496
    maxY = 23220

    currentMinX = minX
    currentMaxX = maxX
    currentMinY = minY
    currentMaxY = maxY

    path = sys.argv[1]

    for z in range(highestZoomLevel, lowestZoomLevel - 1, -1):
        nextZ = z + 1

        if not os.path.exists(path + '%d/' % nextZ):
            raise Exception('The next zoom level (%d) is not present in the path you provided.' % nextZ)

        currentMinX = int(currentMinX / 2.0)
        currentMaxX = int(currentMaxX / 2.0)
        currentMinY = int(currentMinY / 2.0)
        currentMaxY = int(currentMaxY / 2.0)

        for x in range(currentMinX, currentMaxX + 1):
            # Create the current directory if it does not exist
            currentDirectory = path + '%d/%d/' % (z, x)

            if not os.path.exists(currentDirectory):
                os.makedirs(currentDirectory)

            for y in range(currentMinY, currentMaxY + 1):
                print('We\'re on zoom level %d, tile %d / %d.' % (z, x, y))

                nextX = x * 2
                nextY = y * 2

                next_images = []

                image1_path = path + '%d/%d/%d.png' % (nextZ, nextX, nextY)
                image2_path = path + '%d/%d/%d.png' % (nextZ, nextX, nextY + 1)
                image3_path = path + '%d/%d/%d.png' % (nextZ, nextX + 1, nextY)
                image4_path = path + '%d/%d/%d.png' % (nextZ, nextX + 1, nextY + 1)

                current_path = path + '%d/%d/%d.png' % (z, x, y)

                if not os.path.exists(current_path) \
                        or is_file_newer_than(image1_path, current_path) \
                        or is_file_newer_than(image2_path, current_path) \
                        or is_file_newer_than(image3_path, current_path) \
                        or is_file_newer_than(image4_path, current_path):
                    next_images.append(get_image_or_transparent(image1_path))
                    next_images.append(get_image_or_transparent(image2_path))
                    next_images.append(get_image_or_transparent(image3_path))
                    next_images.append(get_image_or_transparent(image4_path))

                    for next_image in next_images:
                        next_image.thumbnail((128, 128), Image.ANTIALIAS)

                    scaled_image = Image.new('RGBA', (256, 256))
                    scaled_image.paste(next_images[0], (0, 0))
                    scaled_image.paste(next_images[1], (0, 128))
                    scaled_image.paste(next_images[2], (128, 0))
                    scaled_image.paste(next_images[3], (128, 128))

                    print('Image neede renewal and has been created, saving...')
                    scaled_image.save(current_path)


if __name__ == "__main__":main()
