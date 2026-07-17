import pyproj
import shapefile

# Eze
lat = 43.727806
long = 7.361583
z_offset = 400
shapefile_dir = "d006/BDTOPO_3-5_TOUSTHEMES_SHP_LAMB93_D006_2026-06-15/BDTOPO/1_DONNEES_LIVRAISON_2026-06-00412/BDT_3-5_SHP_LAMB93_D006_ED2026-06-15/BATI"

# Carcassonne
lat = 43.206602
long = 2.363916
z_offset = 150
shapefile_dir = "d011/BDTOPO_3-5_TOUSTHEMES_SHP_LAMB93_D011_2026-06-15/BDTOPO/1_DONNEES_LIVRAISON_2026-06-00412/BDT_3-5_SHP_LAMB93_D011_ED2026-06-15/BATI"

shapefile_building = "BATIMENT.shp"
shapefile_linear = "CONSTRUCTION_LINEAIRE.shp"

# Shape Fields
#                      +         --- Z_MAX_TOIT
#                     / \         |
#                    /   \        |
#                   /     \       |
#                  /       \      |
#  HAUTEUR ---    +---------+     |  --- Z_MIN_TOIT
#           |     |         |     |   |
#           |     |         |     |   |
#           |     |         |     |   |
#           |     |       _-+     |   |  --- Z_MAX_SOL
#           |     |    _-         |   |   |
#           |     | _-            |   |   |
#          ---    +               |   |   |  --- Z_MIN_SOL
#                                 |   |   |   |
#                                 |   |   |   |
#                 ------------------------------- 0
#
# The building shape describes the roof outline or gutter-line at Z_MIN_TOIT, but the
# individual points may have different Z values. In this case:
#  Z_MIN_TOIT is the lowest point on the roof outline
#  HAUTEUR is the distance from Z_MIN_SOL to the highest point on the roof outline
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
	"NATURE",  # Architecture type: Arc de triomphe | Arène ou théâtre antique | Chapelle | Château | Eglise | Fort, blockhaus, casemate | Indifférenciée | Industriel, agricole ou commercial | Monument | Moulin à vent | Serre | Silo | Tour, donjon | Tribune
	# USAGE1 - How building is used: Agricole | Annexe | Commercial et services | Indifférencié | Industriel | Religieux | Résidentiel | Sportif
	# USAGE2 - Secondary building use: Sans valeur | Agricole | Annexe | Commercial et services | Indifférencié | Industriel | Religieux | Résidentiel | Sportif
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

# Initialize the transformer with always_xy=True to enforce (Longitude, Latitude) order
transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)

x, y = transformer.transform(long, lat)
print(x,y)


sfBuilding = shapefile.Reader(f"{shapefile_dir}/{shapefile_building}")
sfLinear = shapefile.Reader(f"{shapefile_dir}/{shapefile_linear}")
#print(sf.fields)

#print(sf)
#shapes = sf.shapes()

# Sample shapes around point
#175387 BBox(xmin=1051310.9, ymin=6301785.6, xmax=1051316.8, ymax=6301791.4)
#175389 BBox(xmin=1051308.5, ymin=6301793.1, xmax=1051316.9, ymax=6301801.7)
#175689 BBox(xmin=1051319.7, ymin=6301787.9, xmax=1051325.2, ymax=6301792.7)
#175690 BBox(xmin=1051318.0, ymin=6301789.1, xmax=1051323.8, ymax=6301794.6)

x_offset = x
y_offset = y

expand = 150
startPoint = 1
nShapesFound = 0
with open("out.obj", "w") as fout:
	fout.write("mtllib material.mtl\n")
	
	# Iterate over records whose bboxes overlap this region.
	bbox = [x - expand, y - expand, x + expand, y + expand]
	if False:
		for shaperec in sfBuilding.iterShapeRecords(bbox = bbox, fields = ShapeFields_Building):
			shape = shaperec.shape
			rec = shaperec.record
			print()
			print(f"{rec['ID']}")
			#print(shape.bbox)
			print(rec.as_dict())
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
					elif rec['Z_MIN_SOL']:
						z = rec['Z_MIN_SOL']
					elif rec['Z_MAX_SOL']:
						z = rec['Z_MAX_SOL']
					else:
						z = 0
				if z > highest_z:
					highest_z = z
				pts.append([p[0]-x, p[1]-y, z - z_offset])
				nPoints += 1
			nShapesFound += 1

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
				fout.write(f" {startPoint + nPoints - index - 1}")
			fout.write("\n")

			if not missing_z:
				max_ground = rec['Z_MAX_SOL']
				if max_ground and max_ground < rec['Z_MIN_TOIT']:
					fout.write(f"# {max_ground} < {rec['Z_MIN_TOIT']} = {max_ground < rec['Z_MIN_TOIT']}\n")
					for p in pts:
						fout.write(f"v {p[0]} {p[1]} {max_ground - z_offset}\n")

					# Bottom walls
					startTop = startPoint
					startBot = startPoint + nPoints	
					for i in range(0, nPoints-1):
						fout.write(f"f {startBot+i} {startTop+i} {startTop+1+i} {startBot+1+i}\n")	
					fout.write(f"f {startBot+1+(nPoints-2)} {startTop+1+(nPoints-2)} {startTop} {startBot}\n")	

					# Bottom face
					fout.write("f")
					for index in range(0, nPoints):
						fout.write(f" {startPoint + nPoints + index}")
					fout.write("\n")
					startPoint += nPoints
			
				min_ground = rec['Z_MIN_SOL']
				if min_ground:
					for p in pts:
						fout.write(f"v {p[0]} {p[1]} {min_ground - z_offset}\n")

					fout.write(f"usemtl {special}lower\n")
					startTop = startPoint
					startBot = startPoint + nPoints
					for i in range(0, nPoints-1):
						fout.write(f"f {startBot+i} {startTop+i} {startTop+1+i} {startBot+1+i}\n")	
					fout.write(f"f {startBot+1+(nPoints-2)} {startTop+1+(nPoints-2)} {startTop} {startBot}\n")	

					# Bottom face
					fout.write("f")
					for index in range(0, nPoints):
						fout.write(f" {startPoint + nPoints + index}")
					fout.write("\n")
					startPoint += nPoints

			startPoint += nPoints

	if True:
		for shaperec in sfLinear.iterShapeRecords(bbox = bbox, fields = ShapeFields_Linear):
			shape = shaperec.shape
			rec = shaperec.record
			print(shape)
			print(rec)
			print(f"  {shape.points_3D}")

			nPoints = 0
			pts = []
			for p in shape.points_3D:
				pts.append([p[0]-x, p[1]-y, p[2] - z_offset])
				nPoints += 1
			nShapesFound += 1

			special = ""
			if not rec['NATURE'] == "Mur":
				special = "special-"

			fout.write(f"o CL_{rec['ID'][8:]}\n")

			for p in pts:
				fout.write(f"v {p[0]} {p[1]} {p[2]}\n")
			for p in pts:
				fout.write(f"v {p[0]} {p[1]} {p[2] - 5}\n")

			startTop = startPoint
			startBot = startPoint + nPoints	
			fout.write(f"usemtl {special}linear\n")
			for i in range(0, nPoints-1):
				fout.write(f"f {startBot+i} {startTop+i} {startTop+1+i} {startBot+1+i}\n")	

			startPoint += 2 * nPoints

print(f"{nShapesFound} shapes found")

