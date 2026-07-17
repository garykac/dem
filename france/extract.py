import getopt
import sys

from building_extractor import BuildingExtractor
from terrain_extractor import TerrainExtractor

def usage():
	print("Usage: %s <options>" % sys.argv[0])
	print("where <options> are:")
	print("  --help  [-h]")
	print("  --verbose  [-v]")
	exit()

def main():
	try:
		opts, args = getopt.getopt(sys.argv[1:],
			'hv',
			['help', 'verbose'])
	except getopt.GetoptError:
		usage()

	verbose = False
	
	for opt, arg in opts:
		if opt in ('-h', '--help'):
			usage()
		if opt in ('-v', '--verbose'):
			verbose = True

	t = TerrainExtractor()
	t.calc_lambert()
	t.find_slab_cell()
	t.expand_cells()
	t.calc_slab_ranges()
	t.export_heightmap()
	x, y = t.get_center()
	
	b = BuildingExtractor()
	b.set_center(x, y)
	b.export()
	
if __name__ == '__main__':
	main()
