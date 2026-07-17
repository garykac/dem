Instead of having a single directory with hundreds of data files, the `data` directory is structured in a way that matches how the JPGIS organizes their data: based on the assigned mesh id.

When downloading the data, place the zip file in a directory that corresponds to the zip file name.

For example, this zip file:

* `FG-GML-513451-DEM1A-20251208.zip`

should be stored in the following directory:

* `data/5134/51/`

Note that the 6 digit sector+quadrant id is split into `5134` and `51` to keep the directory sizes manageable.

