import argparse
import sys

from building_extractor import BuildingExtractor
from terrain_extractor import TerrainExtractor

def main():
	parser = argparse.ArgumentParser(
		description='Extract DEM and building shape data for France',
		usage=f"{sys.argv[0]} <dept> <lat> <long> [options]")
	parser.add_argument('dept', help="Department number, formatted as: 'd000'")
	parser.add_argument('lat', type=float, help="Latitude")
	parser.add_argument('long', type=float, help="Longitude")
	parser.add_argument('--data', default="data", help="Data directory, default = '%(default)s'")
	parser.add_argument('-v', '--verbose', action='store_true')
	parser._positionals.title = "where"
	parser._optionals.title = "and [options] are"
	args = parser.parse_args()
	
	t = TerrainExtractor(args)
	t.calc_lambert()
	t.find_slab_cell()
	t.expand_cells()
	t.calc_slab_ranges()
	t.export_heightmap()
	x, y = t.get_center()
	
	b = BuildingExtractor(args)
	b.set_center(x, y)
	b.export()
	
if __name__ == '__main__':
	main()
