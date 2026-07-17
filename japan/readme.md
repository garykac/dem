Japan Elevation Data

These are scripts to process digital elevation data for Japan and generate .obj files.

## Usage



## Setup

* [Download data files from JPGIS](jpgis.md)
* Copy the downloaded zip files into [appropriate subdirectories in the data directory](data/readme.md).

Python script dependencies:

* lxml - to parse XML files
* numpy - to manage arrays of data
* PIL - to generate crude thumbnail images for debugging
* pyproj - to calculate projections (lat/long)
* zipfile - to process zip files without extracting them

## Caveats

Even though the data files are ostensibly sampled on a 1 meter (or 5 meter) grid, the data points are only approximately spaced at 1 (or 5) meter. This is because of the projection used: each mesh is bounded by regularly spaced latitude and longitude lines, and one degree of longitude is much wider at lower latitudes than it is as higher latitudes.

Because of this the width of a sector at high latitudes (like Hokkaido) is 1019 meters, which the width at lower latitudes (like Kyushu) is 1202 meters. Since all sectors contain 1125 x 750 data points (for DEM1A), that means the horiontal spacing between points varies from 0.91m to 1.07m.

The vertical spacing between points also varies, but only slightly - from 923.8m (Kyushu) to 925.8m (Hokkaido).
