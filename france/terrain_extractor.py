import os
import pyproj


terrain_dataset_info = [
	"Data source IGNF_RGE-ALTI",
	"  Institut National de l'Information Géographique et Forestière (IGN)",
	"  Référentiel à grande échelle (RGE)",
	"Modèle Numérique de Terrain (MNT = DEM)",
	"URL: https://cartes.gouv.fr/rechercher-une-donnee/dataset/IGNF_RGE-ALTI",
]

METER = 1
KILOMETER = 1000

dept_info = {
	"d006": {
		"name": "Alpes-Maritimes",
		"mnt_path": [
			"RGEALTI_2-0_1M_ASC_LAMB93-IGN69_D006_2024-02-02",
			"RGEALTI",
			"1_DONNEES_LIVRAISON_2024-03-00239",
			"RGEALTI_MNT_1M_ASC_LAMB93_IGN69_D006_20240326",
		],
	},
	"d011": {
		"name": "Aude",
		"mnt_path": [
			"RGEALTI_2-0_1M_ASC_LAMB93-IGN69_D011_2024-11-26",
			"RGEALTI",
			"1_DONNEES_LIVRAISON_2024-12-00020",
			"RGEALTI_MNT_1M_ASC_LAMB93_IGN69_D011_20241209",
		],
	},
	"d013": {
		"name": "Bouches-du-Rhône",
		"mnt_path": [
			"RGEALTI_2-0_1M_ASC_LAMB93-IGN69_D013_2022-12-16",
			"RGEALTI",
			"1_DONNEES_LIVRAISON_2023-01-00125",
			"RGEALTI_MNT_1M_ASC_LAMB93_IGN69_D013_20230113",
		],
	},
	"d050": {
		"name": "Manche",
		"mnt_path": [
			"RGEALTI_2-0_1M_ASC_LAMB93-IGN69_D050_2022-12-21",
			"RGEALTI",
			"1_DONNEES_LIVRAISON_2024-03-00239",
			"RGEALTI_MNT_1M_ASC_LAMB93_IGN69_D050_20240326",
		],
	},
}

class TerrainExtractor():

	def __init__(self, options):
		#self.set_latlong("d006", 43.765238, 7.459564, "Chateau Medieval in Roquebrune Cap Martin")
		#self.set_latlong("d006", 43.727899, 7.361483, "Eze - Jardin")
		#self.set_latlong("d050", 48.63598495012916, -1.5113454743018682, "Mont St Michel")
		self.set_latlong("d011", 43.206602, 2.363916, "Carcassonne")
		#self.set_latlong("d013", 43.284287, 5.371359, "Basilique Notre-Dame de la Garde, Marseille")

		# Test lat/long locations.
		# Span 2 tiles:
		#self.set_latlong("d006", 43.723498, 7.358634)  # Eze - near left tile boundary
		#self.set_latlong("d006", 43.765238, 7.459564)  # Roquebrune Cap Martin - near right tile boundary
		#self.set_latlong("d006", 43.729094, 7.361902)  # Eze - near top tile boundary
		#self.set_latlong("d006", 43.730307, 7.362084)  # Eze - near bottom tile boundary
		# Span 4 tiles:
		#self.set_latlong("d006", 43.730199, 7.357503)  # Eze - near lower right corner
		#self.set_latlong("d006", 43.729218, 7.358721)  # Eze - near upper left corner

		# Calculated Lambert 93 coordinates.
		self.lamb_x = None
		self.lamb_y = None
		
		# Name of the 1km x 1km slab that contains the point.
		# This is the Lambert coordinate of the upper left corner cell in the slab.
		self.slab_x = None
		self.slab_y = None

		# Remainder part of the Lambert coordinate, after dividing by 1000.
		# This is used to identify the cell within the slab.
		self.slab_rx = None
		self.slab_ry = None

		# Cell within the slab that contains the point (relative to lower left
		# cell in the slab).
		self.cell_x = None
		self.cell_y = None
		
		# Size of the neighborhood around the point in each direction.
		# Setting this to 10 (for example) will expand this distance so it
		# includes 10 cells above, below, left and right of the calculated
		# center.
		# MAX = 500 (to avoid spanning too many tiles)
		self.extend_x = 250 * METER
		self.extend_y = 250 * METER
		self.size_x = self.extend_x * 2
		self.size_y = self.extend_y * 2

		# The index of the upper left cell of the range around the point that we want
		# to copy.
		# Note that this is relative to the initial slab, and the cell index may extend
		# outside this slab. In this case, neighboring slabs will need to be used to get
		# the correct cell data.
		self.start_x = None
		self.start_y = None
		
		# The x,y center of the exported mesh in Lambert 93 coordinates.
		self.center_x = None
		self.center_y = None
		
		self.heightmap = None
		self.obj_outfile = "out.obj"

	def set_latlong(self, dept, lat, long, desc=None):
		self.dept = dept
		self.latitude = lat
		self.longitude = long
		self.desc = desc

	# Get the terrain center (in Lambert93).
	def get_center(self):
		return self.center_x, self.center_y

	# Convert latitude/longitude to Lambert 93 projection values.
	def calc_lambert(self):

		# Source/Dest coordinate systems.
		# Source is lat/long = "WGS84" = "EPSG:4326"
		coordSrc = "EPSG:4326"
		# Dest is Lambert-93 = "EPSG:2154"
		coordDst = "EPSG:2154"
		#print(coordSrc, coordDst)

		# Transform coordinates.
		transformer = pyproj.Transformer.from_crs(coordSrc, coordDst, always_xy=True)
		self.lamb_x, self.lamb_y = transformer.transform(self.longitude, self.latitude)
		#print(f"Lambert93: {self.lamb_x}, {self.lamb_y}")

	# Find the slab and cell that contain the specified point.
	def find_slab_cell(self):
		# Each slab is 1000x1000.

		self.slab_x = int(self.lamb_x / KILOMETER)
		self.slab_y = int(self.lamb_y / KILOMETER) + 1
		print(self.slab_x, self.slab_y)

		self.slab_rx = self.lamb_x % KILOMETER
		self.slab_ry = self.lamb_y % KILOMETER
		print(self.slab_rx, self.slab_ry)

		# Cells are arranged in the slab with origin in lower left:
		#
		#    y ^
		#      |
		#      +---->
		#          x

		# Calc cell that contains the original point (x,y relative to origin cell
		# in lower left).
		self.cell_x = int(self.slab_rx + 0.5)
		self.cell_y = int(self.slab_ry + 0.5)
		print(self.cell_x, self.cell_y)

	# Expand the neighborhood around the cell.
	def expand_cells(self):
		# Start by finding the 2x2 grid of cells that surround this point,
		# keeping it as close to the center as possible. This gives a
		# neighborhood distance of 1 around the point, which we can later
		# expand.
		#
		#      +-------+          +-------+          +-------+          +-------+
		#      | *     |          |     * |          |       |          |       |
		#      |   +   |          |   +   |          |   +   |          |   +   |
		#      |       |          |       |          | *     |          |     * |
		#      +-------+          +-------+          +-------+          +-------+
		#          |                  |                  |                  |
		#          v                  v                  v                  v
		#
		#  +-------+-------+  +-------+-------+  +-------+-------+  +-------+-------+
		#  |       |       |  |       |       |  |       |       |  |       |       |
		#  |   +   |   +   |  |   +   |   +   |  |   +   |   +   |  |   +   |   +   |
		#  |       |       |  |       |       |  |       | *     |  |     * |       |
		#  +-------+-------+  +-------+-------+  +-------+-------+  +-------+-------+
		#  |       | *     |  |     * |       |  |       |       |  |       |       |
		#  |   +   |   +   |  |   +   |   +   |  |   +   |   +   |  |   +   |   +   |
		#  |       |       |  |       |       |  |       |       |  |       |       |
		#  +-------+-------+  +-------+-------+  +-------+-------+  +-------+-------+
		#    dx=-1 ; dy=1        dx=0 ; dy=1       dx=-1 ; dy=0        dx=0 ; dy=0

		# Calc offset from center of cell.
		fract_x = self.slab_rx - self.cell_x
		fract_y = self.slab_ry - self.cell_y
		print(fract_x, fract_y)

		# Calc offset from this cell to the upper-left cell of the 2x2 grid.
		dx = 0
		dy = 0
		if fract_x < 0:
			dx = -1
		if fract_y > 0:
			dy = 1
		print(dx, dy)

		# |x|,|y| are the indices of the upper left cell.
		x = self.cell_x + dx
		y = self.cell_y + dy
		print(x, y)

		# Calculate the center of the 2x2 grid in Lambert coordinates.
		self.center_x = (self.slab_x * KILOMETER) - 0.5 + x + 1
		self.center_y = (self.slab_y * KILOMETER) - 0.5 + y + 1

		# Data points are stored in the slab starting with the upper left, so
		# we need to invert the y-axis.
		y = KILOMETER - y

		# Now that we have this 2x2 grid that defines the center of our region,
		# we can expand it equally in all directions. We consider this 2x2 grid
		# to have a distance of 1 around the center point (where the 4 cells
		# meet).
		#
		# For example, expanding to a neighborhood of size 3 would result in an 6x6
		# grid (extending 3 in each direction):
		# 
		#   +---+---+---+---+---+---+
		#   |   |   |   |   |   |   |
		#   +---+---+---+---+---+---+
		#   |   |   |   |   |   |   |
		#   +---+---+---+---+---+---+
		#   |   |   |   |   |   |   |
		#   +---+---+---o---+---+---+  o = calculated center
		#   |   |   |   |*  |   |   |  * = specified coordinate (e.g.)
		#   +---+---+---+---+---+---+
		#   |   |   |   |   |   |   |
		#   +---+---+---+---+---+---+
		#   |   |   |   |   |   |   |
		#   +---+---+---+---+---+---+
		self.start_x = x + 1 - self.extend_x
		self.start_y = y + 1 - self.extend_y
		end_x = self.start_x + self.size_x
		end_y = self.start_y + self.size_y
		print(f"({self.start_x}, {self.start_y}) + ({self.size_x}, {self.size_y}) => ({end_x}, {end_y})")

	def calc_slab_ranges(self):
		slab_x = self.slab_x
		slab_y = self.slab_y
		start_x = self.start_x
		start_y = self.start_y
		size_x = self.size_x
		size_y = self.size_y
		end_x = start_x + size_x
		end_y = start_y + size_y
		
		# Assume simple case - all data from a single slab.
		slab_copy_info = [
			{
				'slab': [slab_x, slab_y],
				'src_xy': [start_x, start_y],
				'size_xy': [size_x, size_y],
				'dst_xy': [0, 0],
			},
		]

		# Check if the data range requires multiple slabs.
		split_x = False
		split_y = False
		if start_x < 0 or end_x > KILOMETER:
			split_x = True
		if start_y < 0 or end_y > KILOMETER:
			split_y = True

		# Ugh. Extends across multiple slabs. More work to do.
		# TODO: Handle spanning 3 or more slabs on one axis.
		if split_x or split_y:
			slab_x1 = slab_x
			slab_y1 = slab_y
			start_x1 = start_x
			start_y1 = start_y
			size_x1 = size_x
			size_y1 = size_y
			dst_x1 = 0
			dst_y1 = 0

			slab_x2 = slab_x
			slab_y2 = slab_y
			start_x2 = start_x
			start_y2 = start_y
			size_x2 = size_x
			size_y2 = size_y
			dst_x2 = 0
			dst_y2 = 0

			if split_x:
				if end_x > KILOMETER:
					# o-----------------+-----------------+  o = origin
					# |                 |                 |
					# |     +---------------------+       |
					# |     |     *               |       |
					# |     +---------------------+       |
					# |                 |                 |
					# +-----------------+-----------------+
					#       |           |         |
					#       |--size_x1--|-size_x2-|
					#    start_x                 end_x
					size_x1 = KILOMETER - start_x

					slab_x2 = slab_x + 1
					start_x2 = 0
					size_x2 = end_x - KILOMETER
					dst_x2 = size_x1
				else:  # start_x < 0
					# +-----------------o-----------------+  o = origin
					# |                 |                 |
					# |       +---------------------+     |
					# |       |              *      |     |
					# |       +---------------------+     |
					# |                 |                 |
					# +-----------------+-----------------+
					#         |         |           |
					#         |-size_x1-|--size_x2--|
					#      start_x                 end_x
					slab_x1 = slab_x - 1
					start_x1 = start_x + KILOMETER
					size_x1 = KILOMETER - start_x1
					
					start_x2 = 0
					size_x2 = end_x
					dst_x2 = size_x1

			if split_y:
				if end_y > KILOMETER:
					#                o = origin
					#              o-----------------+
					#              |                 |
					# start_y ---- |    +-----+      | ----
					#              |    |  *  |      |   |> size_y1
					#              +----|     |------+ ----
					#              |    |     |      |   |> size_y2
					#   end_y ---- |    +-----+      | ----
					#              |                 |
					#              +-----------------+ ----
					size_y1 = KILOMETER - start_y
					
					slab_y2 = slab_y - 1
					start_y2 = 0
					size_y2 = end_y - KILOMETER
					dst_y2 = size_y1
				else:  # start_y < 0
					#                o = origin
					#              +-----------------+
					#              |                 |
					# start_y ---- |    +-----+      | ----
					#              |    |     |      |   |> size_y1
					#              o----|     |------+ ----
					#              |    |  *  |      |   |> size_y2
					#   end_y ---- |    +-----+      | ----
					#              |                 |
					#              +-----------------+ ----
					slab_y1 = slab_y + 1
					start_y1 = start_y + KILOMETER
					size_y1 = KILOMETER - start_y1
					
					start_y2 = 0
					size_y2 = end_y
					dst_y2 = size_y1

			if split_x and split_y:
					#  +-------------+-------------+
					#  |             |             |
					#  |    x1 y1    |    x2 y1    |
					#  |             |             |
					#  +-------------+-------------+
					#  |             |             |
					#  |    x1 y2    |    x2 y2    |
					#  |             |             |
					#  +-------------+-------------+
				slab_copy_info = [
					{
						'slab': [slab_x1, slab_y1],
						'src_xy': [start_x1, start_y1],
						'size_xy': [size_x1, size_y1],
						'dst_xy': [dst_x1, dst_y1],
					},
					{
						'slab': [slab_x1, slab_y2],
						'src_xy': [start_x1, start_y2],
						'size_xy': [size_x1, size_y2],
						'dst_xy': [dst_x1, dst_y2],
					},
					{
						'slab': [slab_x2, slab_y1],
						'src_xy': [start_x2, start_y1],
						'size_xy': [size_x2, size_y1],
						'dst_xy': [dst_x2, dst_y1],
					},
					{
						'slab': [slab_x2, slab_y2],
						'src_xy': [start_x2, start_y2],
						'size_xy': [size_x2, size_y2],
						'dst_xy': [dst_x2, dst_y2],
					},
				]
			else:
				slab_copy_info = [
					{
						'slab': [slab_x1, slab_y1],
						'src_xy': [start_x1, start_y1],
						'size_xy': [size_x1, size_y1],
						'dst_xy': [dst_x1, dst_y1],
					},
					{
						'slab': [slab_x2, slab_y2],
						'src_xy': [start_x2, start_y2],
						'size_xy': [size_x2, size_y2],
						'dst_xy': [dst_x2, dst_y2],
					},
				]

		self.copy_slabs(slab_copy_info)

	def calc_mnt_path(self):
		mnt_path = [ "data", self.dept ]
		mnt_path.extend(dept_info[self.dept]["mnt_path"])
		return mnt_path
	
	# Copy from slabs into |heightmap|.
	def copy_slabs(self, slab_copy_info):
		self.heightmap = [[0 for _ in range(self.size_x)] for _ in range(self.size_y)]
		self.slabs = []
		
		mnt_path = self.calc_mnt_path()
		print(mnt_path)
		for s in slab_copy_info:
			slab_x, slab_y = s['slab']
			start_x, start_y = s['src_xy']
			size_x, size_y = s['size_xy']
			end_x = start_x + size_x
			end_y = start_y + size_y
			hm_x, hm_y = s['dst_xy']
	
			# Slab filename format:
			slab_file = f"RGEALTI_FXX_{slab_x:04}_{slab_y:04}_MNT_LAMB93_IGN69.asc"
			self.slabs.append([slab_x, slab_y])
			print(slab_file)
			print(f"({start_x}, {start_y}) + ({size_x}, {size_y}) -> ({end_x}, {end_y}) @ ({hm_x}, {hm_y})")

			slab_path = os.path.join(*mnt_path, slab_file)

			# Copy data from slab into |heightmap|.
			with open(slab_path, "r") as fp:
				# Skip over header.
				# BUG: Assumes header is exactly 6 lines.
				n = 0
				while n < 6:
					n += 1
					line = fp.readline()
					#print(line.rstrip())
				row = 0
				x = 0
				y = 0
				while line:
					line = fp.readline()
					#print(row, start_y, size_y)
					if row >= start_y and row < end_y:
						x = 0
						#print(line.rstrip())
						data = line.strip().split(' ')
						for col in range(start_x, end_x):
							self.heightmap[hm_y + y][hm_x + x] = data[col]
							x += 1
						y += 1
					row += 1

	# Export |heightmap| to 3d .obj file.
	def export_heightmap(self):
		if not self.heightmap:
			print("Invalid heightmap")
			return
		
		with open(self.obj_outfile, "wt") as fout:
			if self.desc:
				fout.write(f"# Terrain around:\n")
				fout.write(f"#   {self.desc}\n")
				fout.write(f"# \n")

			for i in terrain_dataset_info:
				fout.write(f"# {i}\n")

			fout.write("#\n")
			fout.write(f"# Location center:\n")
			fout.write(f"#   Lat/Long: {self.latitude}, {self.longitude}\n")
			fout.write(f"#   Lambert93: {self.lamb_x}, {self.lamb_y}\n")
			fout.write(f"# Extending:\n")
			fout.write(f"#   X: +/-{self.extend_x} meters\n")
			fout.write(f"#   Y: +/-{self.extend_y} meters\n")
			fout.write(f"# \n")
			fout.write(f"# Data extracted from slabs/dalles:\n")
			for s in self.slabs:
				fout.write(f"#  {s[0]:04}, {s[1]:04}\n")
			fout.write("\n")

			fout.write("g terrain\n")

			# Export vertices by adding x,y to each z value in the heightmap.
			# Adjust start x,y so that the center of the terrain is (0,0)/
			y = self.extend_y - 0.5
			for row in range(0, self.size_y):
				x = 0.5 - self.extend_x
				for col in range(0, self.size_x):
					fout.write(f"v {x} {y} {self.heightmap[row][col]}\n")
					x += 1
				y -= 1

			# Connect points with faces to create terrain.
			# We have vertices indexed as follows (where s is |size|):
			#   1   2   3   4   ...   s
			#  s+1 s+2 s+3 s+4  ...  2*s
			#  ...
			row = 0
			for r in range(1, self.size_y):
				next = row + self.size_x
				for col in range(1, self.size_x):
					fout.write(f"f {row+col} {row+col+1} {next+col+1} {next+col}\n")
				row = next
