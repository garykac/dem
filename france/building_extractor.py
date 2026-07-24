import os
import pathlib
import re
import shapefile
import sys
import zipfile

# Shape Fields for buildings
#                      +         --- Z_MAX_TOIT (Max roof)
#                     / \         |
#                    /   \        |
#                   /     \       |
#                  /       \      |
#  HAUTEUR ---    +---------+     |  --- Z_MIN_TOIT (Min roof)
#  Height   |     |         |     |   |
#           |     |         |     |   |
#           |     |         |     |   |
#           |     |       _-+     |   |  --- Z_MAX_SOL (Max ground)
#           |     |    _-         |   |   |
#           |     | _-            |   |   |
#          ---    +               |   |   |  --- Z_MIN_SOL (Min ground)
#                                 |   |   |   |
#                                 |   |   |   |
#                 ------------------------------- 0
#
# The building shape describes the roof outline or gutter-line at Z_MIN_TOIT, but the
# individual points may have different Z values. In this case:
#   Z_MIN_TOIT is the lowest point on the roof outline
#   HAUTEUR is the distance from Z_MIN_SOL to the highest point on the roof outline
#
# List of relevant fields to extract.
ShapeFields_Building = [
	# DeletionFlag
	"ID",  # Identifier: 24 char: 8 char Class + 16 char numeric code
	# DATE_CREAT - Date this record was first recorded
	# DATE_MAJ - Date this record was last modified
	# DATE_APP - Date of construction
	# DATE_CONF - Most recent date building was attested
	# SOURCE - Source of object data
	# ID_SOURCE - Source for this record's data
	# ACQU_PLANI - Primary method used to acquire planar (x,y) data
	# ACQU_ALTI - Primary method used to acquire altitude (z) data
	# PREC_PLANI - Planar accuracy (in meters)
	# PREC_ALTI - Altitude accuracy (in meters)
	
	# Bati Fields
	# ETAT - Condition of the building: En construction | En projet | En ruine | En service
	# ORIGIN_BAT - Where this shape's data came from: Autre | Cadastre | Imagerie aérienne | Lidar HD

	# Batiment Fields
	"NATURE",  # Architecture type: Arc de triomphe | Arène ou théâtre antique | Chapelle
	           # | Château | Eglise | Fort, blockhaus, casemate | Indifférenciée
	           # | Industriel, agricole ou commercial | Monument | Moulin à vent | Serre
	           # | Silo | Tour, donjon | Tribune
	# USAGE1 - How building is used: Agricole | Annexe | Commercial et services
	           # | Indifférencié | Industriel | Religieux | Résidentiel | Sportif
	# USAGE2 - Secondary building use: Sans valeur | Agricole | Annexe
	           # | Commercial et services | Indifférencié | Industriel | Religieux
	           # | Résidentiel | Sportif
	# LEGER - A lightweight structure: one without a foundation, or open on one side
	# NB_LOGTS - Number of dwellings in building
	# NB_ETAGES - Number of floors in building
	# MAT_MURS - Wall materials (as 2 char code)
	# MAT_TOITS - Roof materials (as 2 char code)
	"HAUTEUR",  # Height from lowest point on ground up to the highest point of the roofline
	"Z_MIN_SOL",  # Altitude of lowest point on the ground at the foot of the building
	"Z_MIN_TOIT",  # Altitude of the roofline (lowest point of the gutter-level outline)
	"Z_MAX_TOIT",  # Altitude of the highest point of the roof (ridge or point)
	"Z_MAX_SOL",  # Altitude of the highest point on the ground at the foot of the building
	# APP_FF - Land registry file matching: Reliability of matching with land registry files
	# IDS_RNB - Identifiers from Référentiel National des Bâtiments
]

# Shape Fields for linear construction (like walls)
ShapeFields_Linear = [
	# DeletionFlag
	"ID",  # Identifier: 24 char: 8 char Class + 16 char numeric code
	# DATE_CREAT - Date this record was first recorded
	# DATE_MAJ - Date this record was last modified
	# DATE_APP - Date of construction
	# DATE_CONF - Most recent date building was attested
	# SOURCE - Source of object data
	# ID_SOURCE - Source for this record's data
	# ACQU_PLANI - Primary method used to acquire planar (x,y) data
	# ACQU_ALTI - Primary method used to acquire altitude (z) data
	# PREC_PLANI - Planar accuracy (in meters)
	# PREC_ALTI - Altitude accuracy (in meters)
	# TOPONYME
	# STATUT_TOP

	# Bati Fields
	# ETAT - Condition of the building: En construction | En projet | En ruine | En service

	# Construction linéaire Fields
	"NATURE",
	# NAT_DETAIL
	# IMPORTANCE
]

METER = 1
KILOMETER = 1000

class BuildingExtractor():

	def __init__(self, opt):
		self.options = opt
		
		# Calculated Lambert 93 coordinates.
		self.lamb_x = opt.lamb_x
		self.lamb_y = opt.lamb_y

		if opt.center_y:
			print("Adjusting center_y")
			opt.center_y -= 1000
		self.z_offset = opt.offset

		self.init_data_dir()
		
		#print(shapefile_dir)
		#print(sf.fields)

		#print(sf)
		#shapes = sf.shapes()

		# Sample shapes around point
		#175387 BBox(xmin=1051310.9, ymin=6301785.6, xmax=1051316.8, ymax=6301791.4)
		#175389 BBox(xmin=1051308.5, ymin=6301793.1, xmax=1051316.9, ymax=6301801.7)
		#175689 BBox(xmin=1051319.7, ymin=6301787.9, xmax=1051325.2, ymax=6301792.7)
		#175690 BBox(xmin=1051318.0, ymin=6301789.1, xmax=1051323.8, ymax=6301794.6)

		self.expand = 50 * METER
		
		self.bbox = [self.lamb_x - self.expand, self.lamb_y - self.expand,
					self.lamb_x + self.expand, self.lamb_y + self.expand]

	def error_missing_data_dir(self):
		print(f"ERROR - unable to find zip file data for {self.options.dept}")
		sys.exit(1)

	def init_data_dir(self):
		base_dir = os.path.join(self.options.data, self.options.dept)

		if not pathlib.Path(base_dir).is_dir():
			self.error_missing_data_dir()

		# Find the .zip file with the most recent data.
		zipDataName = None
		zipDataDate = "1900-01-01"
		for f in pathlib.Path(base_dir).iterdir():
			if f.is_file():
				m = re.fullmatch(r'BDTOPO_3-5_TOUSTHEMES_SHP_LAMB93_(....)_(....-..-..).zip', f.name)
				if m:
					date = m.group(2)
					if date > zipDataDate:
						zipDataDate = date
						zipDataName = f.name
		if not zipDataName:
			self.error_missing_data_dir()

		path = [self.options.data, self.options.dept]		
		zipPath = os.path.join(*path, zipDataName)

		buildingPath = None
		linearPath = None
		with zipfile.ZipFile(zipPath, "r") as z:
			for f in sorted(z.namelist()):
				m = re.fullmatch(r'BDTOPO_3-5_TOUSTHEMES_SHP_LAMB93_.*/BATI/BATIMENT.shp', f)
				if m:
					buildingPath = f
				m = re.fullmatch(r'BDTOPO_3-5_TOUSTHEMES_SHP_LAMB93_.*/BATI/CONSTRUCTION_LINEAIRE.shp', f)
				if m:
					linearPath = f

		self.shapefile_building_path = os.path.join(zipPath, buildingPath)
		self.shapefile_linear_path = os.path.join(zipPath, linearPath)

	def export_building(self, fout):
		sfBuilding = shapefile.Reader(f"{self.shapefile_building_path}")
		for shaperec in sfBuilding.iterShapeRecords(bbox = self.bbox, fields = ShapeFields_Building):
			shape = shaperec.shape
			rec = shaperec.record
			#print()
			#print(f"{rec['ID']}")
			#print(shape.bbox)
			#print(rec.as_dict())
			print(f"  {shape.points_3D}")
			height = rec['HAUTEUR']
			nPoints = 0
			highest_z = -1000
			missing_z = False
			pts = []
			for p in shape.points_3D:
				z = p[2]
				if z < -500:
					missing_z = True
					if rec['Z_MIN_TOIT']:
						z = rec['Z_MIN_TOIT']
					elif rec['Z_MAX_TOIT']:
						z = rec['Z_MAX_TOIT']
					elif rec['Z_MIN_SOL']:
						z = rec['Z_MIN_SOL']
					elif rec['Z_MAX_SOL']:
						z = rec['Z_MAX_SOL']
					else:
						z = 0

				zRoofMin = None
				if rec['Z_MIN_TOIT']:
					zRoofMin = rec['Z_MIN_TOIT']
				elif rec['Z_MAX_TOIT']:
					zRoofMin = rec['Z_MAX_TOIT']

				zGroundMax = None
				if rec['Z_MAX_SOL']:
					zGroundMax = rec['Z_MAX_SOL']
				elif rec['Z_MIN_SOL']:
					zGroundMax = rec['Z_MIN_SOL']

				if not self.options.center_x:
					self.options.center_x = p[0]
					self.options.center_y = p[1]
					print(f"Setting center_x,y to {p[0]}, {p[1]}")

				pts.append([p[0] - self.options.center_x, p[1] - self.options.center_y, z - self.z_offset])

				if z > highest_z:
					highest_z = z
				nPoints += 1
			self.nShapesFound += 1

			# Remove endpoint if it matches the start point.
			if pts[0] == pts[nPoints-1]:
				pts.pop()
				nPoints -= 1

			fout.write(f"\n")
			fout.write(f"# {rec['ID']}")
			if rec['HAUTEUR']:
				fout.write(f"  Height: {rec['HAUTEUR']}")
			fout.write("\n")

			special = ""
			if not rec['NATURE'] == "Indifférenciée":
				special = "special-"
				fout.write(f"# {rec['NATURE']}\n")

			if rec['Z_MIN_SOL'] or rec['Z_MAX_SOL']:
				fout.write(f"# Ground min: {rec['Z_MIN_SOL']}, max: {rec['Z_MAX_SOL']}\n")
			if rec['Z_MIN_TOIT'] or rec['Z_MAX_TOIT']:
				fout.write(f"# Roof min: {rec['Z_MIN_TOIT']}, max: {rec['Z_MAX_TOIT']}\n")

			fout.write(f"o BA_{rec['ID'][8:]}\n")

			for p in pts:
				fout.write(f"v {p[0]} {p[1]} {p[2]}\n")

			# Top face
			fout.write(f"usemtl {special}upper\n")
			fout.write("f")
			for index in range(0, nPoints):
				fout.write(f" {self.startPoint + nPoints - index - 1}")
			fout.write("\n")

			if True:  #not missing_z:
				max_ground = rec['Z_MAX_SOL']
				if max_ground and max_ground < zRoofMin:
					fout.write(f"# {max_ground} < {zRoofMin} = {max_ground < zRoofMin}\n")
					for p in pts:
						fout.write(f"v {p[0]} {p[1]} {max_ground - self.z_offset}\n")

					# Bottom walls
					startTop = self.startPoint
					startBot = self.startPoint + nPoints	
					for i in range(0, nPoints-1):
						fout.write(f"f {startBot+i} {startTop+i} {startTop+1+i} {startBot+1+i}\n")	
					fout.write(f"f {startBot+1+(nPoints-2)} {startTop+1+(nPoints-2)} {startTop} {startBot}\n")	

					# Bottom face
					fout.write("f")
					for index in range(0, nPoints):
						fout.write(f" {self.startPoint + nPoints + index}")
					fout.write("\n")
					self.startPoint += nPoints
			
				min_ground = rec['Z_MIN_SOL']
				if min_ground:
					for p in pts:
						fout.write(f"v {p[0]} {p[1]} {min_ground - self.z_offset}\n")

					fout.write(f"usemtl {special}lower\n")
					startTop = self.startPoint
					startBot = self.startPoint + nPoints
					for i in range(0, nPoints-1):
						fout.write(f"f {startBot+i} {startTop+i} {startTop+1+i} {startBot+1+i}\n")	
					fout.write(f"f {startBot+1+(nPoints-2)} {startTop+1+(nPoints-2)} {startTop} {startBot}\n")	

					# Bottom face
					fout.write("f")
					for index in range(0, nPoints):
						fout.write(f" {self.startPoint + nPoints + index}")
					fout.write("\n")
					self.startPoint += nPoints

			self.startPoint += nPoints
	
	def export_linear_constuction(self, fout):
		sfLinear = shapefile.Reader(f"{self.shapefile_linear_path}")
		for shaperec in sfLinear.iterShapeRecords(bbox = self.bbox, fields = ShapeFields_Linear):
			shape = shaperec.shape
			rec = shaperec.record
			#print(shape)
			#print(rec)
			#print(f"  {shape.points_3D}")

			if rec['NATURE'] in ["Tunnel"]:
				continue

			nPoints = 0
			pts = []
			for p in shape.points_3D:
				z = p[2]
				if z < -500:
					z = 0

				pts.append([p[0] - self.options.center_x, p[1] - self.options.center_y, z - self.z_offset])
				nPoints += 1
			self.nShapesFound += 1

			special = ""
			if not rec['NATURE'].startswith("Mur"):
				special = "special-"

			fout.write(f"\n")
			fout.write(f"# {rec['ID']} - {rec['NATURE']}\n")
			fout.write(f"o CL_{rec['ID'][8:]}\n")

			for p in pts:
				fout.write(f"v {p[0]} {p[1]} {p[2]}\n")
			for p in pts:
				# Give an arbitrary height (5m) to the line.
				fout.write(f"v {p[0]} {p[1]} {p[2] - 5}\n")

			startTop = self.startPoint
			startBot = self.startPoint + nPoints	
			fout.write(f"usemtl {special}linear\n")
			for i in range(0, nPoints-1):
				fout.write(f"f {startBot+i} {startTop+i} {startTop+1+i} {startBot+1+i}\n")	

			self.startPoint += 2 * nPoints

	def export(self):
		self.startPoint = 1
		self.nShapesFound = 0
		with open("out2.obj", "w") as fout:
			fout.write("mtllib material.mtl\n")
			self.export_building(fout)
			self.export_linear_constuction(fout)

		print(f"{self.nShapesFound} shapes found")
