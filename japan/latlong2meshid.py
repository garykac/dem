import sys

# The map of Japan is divided into meshes, and each mesh is assigned a Mesh ID, which
# is broken into 3 parts:
#   TTGG - Region: TT encodes latitude, GG is the last 2 digits of the longitude.
#   QQ - The x,y quadrant of the region, each ranging from 0-7
#   CC - The x,y cell of the quadrant, each ranging from 0-9
# 
# Note that region/quadrant/cell are not the official names for these divisions. The
# documentation refers to them simply as primary, secondary and tertiary mesh ids.
# 
# Each region covers 1 full degree of longitude and 2/3rds of a degree of latitude:
# 
#                                            Longitude:
#                         |         138           |         139           |
#   TT:    Latitude:          
#                         |                       |                       |
#       -  36.0      -----+-----------------------+-----------------------+----
#                         |                       |                       |
#                         |                       |                       |
#                         |                       |                       |
#   53                    |         5338          |         5339          |
#                         |                       |                       |
#                         |                       |                       |
#                         |                       |                       |
#       -  35.33333  -----+-----------------------+-----------------------+----
#                         |                       |                       |
#                         |                       |                       |
#                         |                       |                       |
#   52                    |         5238          |         5339          |
#                         |                       |                       |
#                         |                       |                       |
#                         |                       |                       |
#       -  34.66666  -----+-----------------------+-----------------------+----
#                         |                       |                       |
#                         |                       |                       |
#                         |                       |                       |
#   51                    |         5138          |         5139          |
#                         |                       |                       |
#                         |                       |                       |
#                         |                       |                       |
#       -  34.0      -----+-----------------------+-----------------------+----
# 
# To calculate region mesh id from lat/long:
#  * TT = int(lat * 1.5)
#  * GG = long - 100
# 
# Region 5239 covers:
#  * Latitude from 34.666666 up to 35.333333
#  * Longitude from 139.00000 up to 139.999999
# 
# 
# Each region is divided into 64 (8x8) quadrants:
#
#                 GG:                38                      39
#          Longitude:     | 138                   | 139                   |
#                         .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
#                         0  1  2  3  5  6  7  8  0  1  2  3  5  6  7  8  0
#                            2  5  7     2  5  7     2  5  7     2  5  7
#                            5     5     5     5     5     5     5     5
#   TT:    Latitude:          
#                         |                       |                       |
#       -  36.0      -----+-----------------------+-----------------------+----
#          35.91666       |                       |                       |
#          35.83333       |                       |                       |
#          35.75          |                       |                       |
#   53     35.66666       |         5338          |         5339          |
#          35.58333       |                       |                       |
#          35.5           |                       |                       |
#          35.41666       |                       |                       |
#       -  35.33333  -----+-----------------------+-----------------------+----
#          35.25          |                       |  .  .  .  .  .  .  .  |
#          35.16666       |                       |  .  .  .  .  .  .  .  |
#          35.08333       |                       |  .  .  .  .  .  .  .  |
#   52     35.0           |         5238          |  .  .  .  .  .  .  .  |
#          34.91666       |                       |  .  .  .  .  .  .  .  |
#          34.83333       |                       |  .  .  .  .  .  .  .  |
#          34.75          |                       |  .  .  .  .  .  .  .  |
#       -  34.66666  -----+-----------------------+-----------------------+----
#          34.58333       |                       |                       |
#          34.5           |                       |                       |
#          34.41666       |                       |                       |
#   51     34.33333       |         5138          |         5139          |
#          34.25          |                       |                       |
#          34.16666       |                       |                       |
#          34.08333       |                       |                       |
#       -  34.0      -----+-----------------------+-----------------------+----
# 
# Each quadrant is indexed 0-7 in each dimension, and identified by a 6-digit id:
# the 4-digit region + 1 digit (0-7) each for the x,y of the quadrant.
# 
#             +------+------+------+------+------+------+------+------+
#             |  70  |  71  |  72  |  73  |  74  |  75  |  76  |  77  |
#             +------+------+------+------+------+------+------+------+
#             |  60  |  61  |  62  |  63  |  64  |  65  |  66  |  67  |
#             +------+------+------+------+------+------+------+------+
#             |  50  |  51  |  52  |  53  |  54  |  55  |  56  |  57  |
#             +------+------+------+------+------+------+------+------+
#             |  40  |  41  |  42  |  43  |  44  |  45  |  46  |  47  |
#             +------+------+------+------+------+------+------+------+
#             |  30  |  31  |  32  |  33  |  34  |  35  |  36  |  37  |
#             +------+------+------+------+------+------+------+------+
#             |  20  |  21  |  22  |  23  |  24  |  25  |  26  |  27  |
#             +------+------+------+------+------+------+------+------+
#             |  10  |  11  |  12  |  13  |  14  |  15  |  16  |  17  |
#             +------+------+------+------+------+------+------+------+
#             |  00  |  01  |  02  |  03  |  04  |  05  |  06  |  07  |
#             +------+------+------+------+------+------+------+------+
# 
# The files that you download from the website correspond to these quadrants.
# 
# Note that some of the quadrants may not be present, as in this example of 5239:
# 
#            139    139    139    139    139    139    139    139    140
#             .0     .125   .25    .375   .5     .625   .75    .875   .0
#  35.33333   +------+------+------+------+------+------+------+------+
#             |  70  |  71  |  72  |  73  |  74  |  75  |  76  |  77  |
#  35.25      +------+------+------+------+------+------+------+------+
#             |  60  |  61  |      |      |  64  |  65  |  66  |  67  |
#  35.16666   +------+------+------+------+------+------+------+------+
#             |  50  |  51  |      |      |  54  |  55  |  56  |  57  |
#  35.08333   +------+------+------+------+------+------+------+------+
#             |  40  |  41  |      |      |      |      | (46) |  47  |
#  35         +------+------+------+------+------+------+------+------+
#             |  30  |  31  |      |      |      |      | (36) | (37) |
#  34.91666   +------+------+------+------+------+------+------+------+
#             |  20  |  21  |      |      |      |      | (26) | (27) |
#  34.83333   +------+------+------+------+------+------+------+------+
#             |  10  |      |  12  |  13  |      |      |      |      |
#  34.75      +------+------+------+------+------+------+------+------+
#             |  00  |      |  02  |  03  |      |      |      |      |
#  34.66666   +------+------+------+------+------+------+------+------+
# 
# Usually, this is because the area is comprised entirely of water (the blank spaces,
# above), but sometimes land areas are missing data (e.g., the numbers shown in
# parentheses, above).
# 
# 
# When you download the data for a quadrant, you'll discover that it is further divided
# into 10x10 cells, indexed as follows:
# 
#     90  91  92  93  94  95  96  97  98  99
#     80  81  82  83  84  85  86  87  88  89
#     70  71  72  73  74  75  76  77  78  79
#     60  61  62  63  64  65  66  67  68  69
#     50  51  52  53  54  55  56  57  58  59
#     40  41  42  43  44  45  46  47  48  49
#     30  31  32  33  34  35  36  37  38  39
#     20  21  22  23  24  25  26  27  28  29
#     10  11  12  13  14  15  16  17  18  19
#     00  01  02  03  04  05  06  07  08  09
# 
# As with the quadrants, individual cell files will be omitted if they don't have data
# available.
# 
# The files
# 
# For the 1 meter meshes, each of these cells contains 1125 x 750 data points, which are
# spaced roughly (but not exactly) 1 meter apart.

# Convert latitude/longitude to JPGIS meshid.
def latlong2meshid(lat, long):
	regionTT = int(lat * 1.5)
	regionGG = int(long - 100)
	
	QX = int(12 * (lat - (regionTT / 1.5)))
	QY = int(8 * ((long - 100) - regionGG))
	
	return f"{regionTT:02}{regionGG:02}{QX}{QY}"

def usage():
	print("Usage: %s <latitude> <longitude>" % sys.argv[0])
	exit()

def main():
	if len(sys.argv) < 3:
		usage()
	if len(sys.argv) > 3:
		print("Unexpected extra arguments. Ignoring all but first 2")
	
	lat = float(sys.argv[1])
	long = float(sys.argv[2])

	meshid = latlong2meshid(lat, long)
	print(f"({lat}, {long}) -> '{meshid}'")

if __name__ == "__main__":
	main()
