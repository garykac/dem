import argparse
import pyproj
import sys

from building_extractor import BuildingExtractor
from terrain_extractor import TerrainExtractor
from locations import LOCATIONS

# Convert latitude/longitude to Lambert 93 projection values.
def calc_lambert(lat, long):
	# Source/Dest coordinate systems.
	# Source is lat/long = "WGS84" = "EPSG:4326"
	coordSrc = "EPSG:4326"
	# Dest is Lambert-93 = "EPSG:2154"
	coordDst = "EPSG:2154"

	# Transform coordinates.
	# |always_xy| is True to enforce (Longitude, Latitude) order.
	transformer = pyproj.Transformer.from_crs(coordSrc, coordDst, always_xy=True)
	lamb_x, lamb_y = transformer.transform(long, lat)
	#print(f"Lambert93: {lamb_x}, {lamb_y}")
	return (lamb_x, lamb_y)

def main():
	parser = argparse.ArgumentParser(
		description='Extract DEM and building shape data for France',
		usage=f"{sys.argv[0]} <dept> <lat> <long> [options]\n    OR {sys.argv[0]} <name> [options]")
	parser.add_argument('dept', nargs='?', metavar="<dept>", help="Department number, formatted as: 'd000'")
	parser.add_argument('lat', type=float, nargs='?', metavar="<lat>", help="Latitude")
	parser.add_argument('long', type=float, nargs='?', metavar="<long>", help="Longitude")
	# The 'name' argument isn't actually used, but is included so it shows in the usage message.
	parser.add_argument('name', nargs='?', metavar="<name>", help="Name of a pre-defined location (see --list)")
	parser.add_argument('--desc', metavar="<desc>", help="Description of lat/long location")
	parser.add_argument('--offset', type=float, metavar="<z-offset>", default=0, help="Z-offset to adjust height in output")
	parser.add_argument('--data', default="data", metavar="<data-dir>", help="Data directory, default = '%(default)s'")
	parser.add_argument('--terrain', action='store_true', help="Extract terrain data")
	parser.add_argument('--building', action='store_true', help="Extract building shape data")
	parser.add_argument('--list', action='store_true', help="Show list of locations")
	parser.add_argument('-v', '--verbose', action='store_true')

	# These aren't real command line arguments, but are just placeholders for calculated
	# values (set below).
	parser.add_argument('--lamb_x', type=float, help=argparse.SUPPRESS)
	parser.add_argument('--lamb_y', type=float, help=argparse.SUPPRESS)
	parser.add_argument('--center_x', type=float, help=argparse.SUPPRESS)
	parser.add_argument('--center_y', type=float, help=argparse.SUPPRESS)

	parser._positionals.title = "where"
	parser._optionals.title = "and [options] are"
	args = parser.parse_args()
	
	# Verify the positional arguments.
	# 'name' is only set if 4 positional arguments were specified, which is too many.
	if args.name:
		print("ERROR - too many arguments")
		parser.print_help()
		sys.exit(0)
	# No positional arguments given.
	if not args.dept:
		# This is OK *only* if the user is asking for a list of locations.
		if args.list:
			for loc in LOCATIONS.keys():
				info = LOCATIONS[loc]
				print(f"  '{loc}': {info['dept']}, {info['lat']}, {info['long']}")
			sys.exit(0)
		else:
			print("ERROR - missing arguments")
			parser.print_help()
			sys.exit(0)
	# Was a valid location name given as the first argument?
	if args.dept in LOCATIONS:
		name = args.dept
		args.dept = LOCATIONS[name]['dept']
		args.lat = LOCATIONS[name]['lat']
		args.long = LOCATIONS[name]['long']
		args.desc = LOCATIONS[name]['desc']
	# Otherwise  make sure we have dept, lat and long.
	elif not args.lat or not args.long:
		print("ERROR - missing arguments")
		parser.print_help()
		sys.exit(0)

	args.lamb_x, args.lamb_y = calc_lambert(args.lat, args.long)

	#print(args)
	if args.terrain:
		t = TerrainExtractor(args)
		t.find_slab_cell()
		t.expand_cells()
		t.calc_slab_ranges()
		t.export_heightmap()
		# Set center so that buildings (if any) are aligned correctly.
		args.center_x, args.center_y = t.get_center()

	if args.building:
		b = BuildingExtractor(args)
		b.export()
	
if __name__ == '__main__':
	main()
