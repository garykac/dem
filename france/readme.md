## France Elevation Data

These are scripts to process digital elevation and building shape data for France and generate .obj files.

## Usage

Import the generated `.obj` file into Blender with Z-up and Y-forward orientation.

## Setup

* [Download and pre-process the data files from cartes.gouv.fr](data/readme.md)

Python script dependencies:

* pyproj - to calculate projections (lat/long)
* pyshp - to parse shape (`.shp`) files

## Caveats

The extracted meshes have the following limitations:

* Generally limited to ~1 sq km in size.
* Cannot span multiple departments (administrative divisions of France)
