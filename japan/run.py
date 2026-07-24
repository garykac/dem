# -*- coding: utf-8 -*-
import argparse
import os
import pyproj
import re
import sys
import zipfile

import numpy as np

from lxml import etree
from pathlib import Path
from PIL import Image

# Data source:
# Geospatial Information Authority of Japan (GSI)
# https://service.gsi.go.jp/kiban/app/map/?search=dem#7/34.0642407247542/134.30544345940302

FGD_NAMESPACE = '{http://fgd.gsi.go.jp/spec/2008/FGD_GMLSchema}'
GML_NAMESPACE = '{http://www.opengis.net/gml/3.2}'

DEM_TYPE_AERIAL_1m = "1mメッシュ（標高）"
DEM_TYPE_AERIAL_5m = "5mメッシュ（標高）"

TYPE_GROUND_LEVEL = "地表面"
TYPE_INLAND_WATER_LEVEL = "内水面"
TYPE_SEA_LEVEL = "海水面"
TYPE_NO_DATA = "データなし"
TYPE_OTHER = "その他"

MIN_ELEVATION = -10000
MAX_ELEVATION = 10000

class ProcessDEM():
	def __init__(self, options):
		self.options = options
		
		self.gen_png = options.png
		self.gen_obj = options.obj
		self.list_cells = options.list

		self.show_info = True
		if self.gen_png or self.gen_obj:
			self.show_info = False
		
		self.mesh_id = options.mesh_id
		self.mid1 = None  # Region (primary)
		self.mid2 = None  # Quadrant (secondary)
		self.mid3 = None  # Cell (tertiary)
		self.mid3_set = None  # Cell (as set by user)
		if len(self.mesh_id) == 6:
			self.mid1 = self.mesh_id[0:4]
			self.mid2 = self.mesh_id[4:6]
		elif len(self.mesh_id) == 8:
			self.mid1 = self.mesh_id[0:4]
			self.mid2 = self.mesh_id[4:6]
			self.mid3 = self.mesh_id[6:8]
			self.mid3_set = self.mesh_id[6:8]
		else:
			error("Invalid mesh id. Expected 6- or 8-digit number")
		
		self.mesh_type = options.dem

		self.filename = None
		self.obj_file = None
		
		self.data = None
		self.dataImg = None
		
		self.root = None
		
		self.mesh_id = None
		
		self.x_start = 0
		self.y_start = 0
		self.x_max = None
		self.y_max = None
		self.lowerLeft = []
		self.upperRight = []
		
		# Min/max value found overall in all files in directory.
		self.dir_max = MIN_ELEVATION
		self.dir_min = MAX_ELEVATION
		
	def error(self, msg):
		print(f"ERROR: {msg}")
		sys.stdout.flush()
		sys.exit(1)
		
	def load(self, fp):
		p = etree.XMLParser(huge_tree=True)
		tree = etree.parse(fp, parser=p)
		self.root = tree.getroot()

		# <Dataset> (root)
		#   <DEM>
		for child in self.root:
			if child.tag == f'{FGD_NAMESPACE}DEM':
				self.process_DEM(child)
	
	# <DEM>
	#   <fid>
	#   <lfspanFr>
	#   <devDate>
	#   <orgGILvl>
	#   <orgMDId>
	#   <type>
	#   <mesh>
	#   <coverage>
	def process_DEM(self, node):
		for child in node:
			if child.tag == f'{FGD_NAMESPACE}type':
				type = child.text
				if not type in [DEM_TYPE_AERIAL_1m, DEM_TYPE_AERIAL_5m]:
					self.error(f"Unexpected mesh data type: {type}")
			if child.tag == f'{FGD_NAMESPACE}mesh':
				self.mesh_id = child.text
			elif child.tag == f'{FGD_NAMESPACE}coverage':
				self.process_coverage(child)

	# <coverage>
	#   <boundedBy>
	#   <gridDomain>
	#   <rangeSet>
	#   <coverageFunction>
	def process_coverage(self, node):
		data = None
		for child in node:
			if child.tag == f'{GML_NAMESPACE}boundedBy':
				self.process_boundedBy(child)
			elif child.tag == f'{GML_NAMESPACE}gridDomain':
				self.process_gridDomain(child)
			elif child.tag == f'{GML_NAMESPACE}rangeSet':
				data = child
			elif child.tag == f'{GML_NAMESPACE}coverageFunction':
				self.process_coverageFunction(child)
		
		# Process the data node last since we need to parse all of the metadata first.
		self.process_rangeSet(data)

	# <boundedBy>
	#   <Envelope>
	#     <lowerCorner>
	#     <upperCorner>
	def process_boundedBy(self, node):
		xlower, ylower = 0, 0
		xupper, yupper = 0, 0
		for child in node:
			if child.tag == f'{GML_NAMESPACE}Envelope':
				proj_full = child.attrib['srsName']
				m = re.fullmatch(r'fguuid:(jgd\d\d\d\d).bl', proj_full)
				proj = None
				if m:
					proj = m.group(1)
				if not m or not proj in ['jgd2011', 'jgd2024']:
					self.error(f"Unexpected projection: {projproj}")
				
				for child2 in child:
					if child2.tag == f'{GML_NAMESPACE}lowerCorner':
						xlower, ylower = child2.text.split()
					if child2.tag == f'{GML_NAMESPACE}upperCorner':
						xupper, yupper = child2.text.split()
		
		# latitude, longitude
		self.lowerLeft = [float(xlower), float(ylower)]
		self.upperRight = [float(xupper), float(yupper)]

	# <gridDomain>
	#   <Grid>
	#     <limits>
	#       <GridEnvelope>
	#         <low>
	#         <high>
	#     <axisLabels>
	def process_gridDomain(self, node):
		xlow, ylow = 0, 0
		xhigh, yhigh = 0, 0
		for child in node:
			if child.tag == f'{GML_NAMESPACE}Grid':
				for child2 in child:
					if child2.tag == f'{GML_NAMESPACE}axisLabels':
						axisLabels = child2.text
						if not axisLabels == "x y":
							self.error(f"Unexpected axisLabels: {axisLabels}")
					elif child2.tag == f'{GML_NAMESPACE}limits':
						for child3 in child2:
							if child3.tag == f'{GML_NAMESPACE}GridEnvelope':
								for child4 in child3:
									if child4.tag == f'{GML_NAMESPACE}low':
										xlow, ylow = child4.text.split()
										#print(f"low: {xlow}, {ylow}")
									if child4.tag == f'{GML_NAMESPACE}high':
										xhigh, yhigh = child4.text.split()
										#print(f"high: {xhigh}, {yhigh}")
		if not (int(xlow) == 0 and int(ylow) == 0):
			self.error(f"Expected xlow,ylow to be 0,0 (instead of {xlow},{ylow})")
		self.x_max = int(xhigh)+1
		self.y_max = int(yhigh)+1
		#print(f"Size: {self.x_max}, {self.y_max}")
	
	# <coverageFunction>
	#   <GridFunction>
	#     <sequenceRule>
	#     <startPoint>
	def process_coverageFunction(self, node):
		xstart = None
		ystart = None
		for child in node:
			if child.tag == f'{GML_NAMESPACE}GridFunction':
				for child2 in child:
					if child2.tag == f'{GML_NAMESPACE}sequenceRule':
						seqRule = child2.text
						seqOrder = child2.attrib['order']
						if not (seqRule == "Linear" and seqOrder == "+x-y"):
							self.error(f"Unexpected sequenceRule: {seqRule} {seqOrder}")
					elif child2.tag == f'{GML_NAMESPACE}startPoint':
						xstart, ystart = child2.text.split()

		self.x_start = int(xstart)
		self.y_start = int(ystart)
	
	# <rangeSet>
	#   <DataBlock>
	def process_rangeSet(self, node):
		for child in node:
			if child.tag == f'{GML_NAMESPACE}DataBlock':
				self.process_DataBlock(child)
	
	# <DataBlock>
	#   <rangeParameters>
	#     <QuantityList>
	#   <tupleList>
	def process_DataBlock(self, node):
		for child in node:
			if child.tag == f'{GML_NAMESPACE}tupleList':
				self.process_tupleList(child)

	def process_tupleList(self, node):
		# PIL Image.fromArray expects the array to be height x width.
		if self.gen_obj:
			self.data = np.zeros((self.y_max, self.x_max), dtype=np.float32)
		if self.gen_png:
			self.dataImg = np.zeros((self.y_max, self.x_max), dtype=np.uint8)

		x, y = 0, 0
		
		if not (self.x_start == 0 and self.y_start == 0):
			while x < self.x_start or y < self.y_start:
				if self.gen_obj:
					self.data[self.y_max-1 - y, x] = 0
				if self.gen_png:
					self.dataImg[y, x] = 255
				x += 1
				if x >= self.x_max:
					x = 0
					y += 1

		dmin = float(MAX_ELEVATION)
		dmax = float(MIN_ELEVATION)
		seenTypes = {}
		firstType = {}
		for line in node.text.splitlines():
			if not line:
				continue
			(t, dstr) = line.split(",")
			data = float(dstr)
			if not t in [TYPE_NO_DATA, TYPE_GROUND_LEVEL, TYPE_INLAND_WATER_LEVEL, TYPE_SEA_LEVEL, TYPE_OTHER]:
				self.error(f"Unexpected data type: {t}")
			
			if not t in seenTypes:
				seenTypes[t] = 1
				firstType[t] = line
			else:
				seenTypes[t] += 1
		
			if t in [TYPE_GROUND_LEVEL, TYPE_INLAND_WATER_LEVEL] and not data == -9999:
				if data > dmax:
					dmax = data
				if data < dmin:
					dmin = data

			if self.gen_obj:
				if t in [TYPE_NO_DATA, TYPE_SEA_LEVEL]:
					self.data[self.y_max-1 - y, x] = 0
				else:
					self.data[self.y_max-1 - y, x] = data

			if self.gen_png:
				if not t in [TYPE_GROUND_LEVEL]:
					data = 255
				if data < 0:
					data = 0
				if data > 255:
					#print(f"> 255: {data}")
					data = 255
				self.dataImg[y, x] = round(data / 2)

			x += 1
			if x >= self.x_max:
				x = 0
				y += 1
				if y > self.y_max:
					self.error(f"Too may rows of data: {y} > {self.y_max}")

		print(f"{self.mid1}-{self.mid2}-{self.mid3}")
		if self.show_info:
			lat0, long0 = self.lowerLeft
			lat1, long1 = self.upperRight
			print(f"  Latitude: {lat0}, {lat1}")
			print(f"  Longitude: {long0}, {long1}")

			geod = pyproj.Geod(ellps='WGS84')
			# 2D distance in meters with longitude, latitude of the points
			az1, az2, topWidth = geod.inv(long0, lat1, long1, lat1)
			az1, az2, bottomWidth = geod.inv(long0, lat0, long1, lat0)
			az1, az2, height = geod.inv(long0, lat0, long0, lat1)
			print("  Size of cell:")
			print(f"    X (at top): {topWidth:.2f} m ({topWidth/self.x_max:.4f} m between points)")
			print(f"    X (at bottom): {bottomWidth:.2f} m ({bottomWidth/self.x_max:.4f} m between points)")
			print(f"    Y: {height:.2f} meters")
			print("  Terrain height:")
			print(f"    Z (min): {dmin}")
			print(f"    Z (max): {dmax}")
			#print(seenTypes)
			#print(firstType)

		# Update overall min/max across files in this directory.
		if dmin < self.dir_min:
			self.dir_min = dmin
		if dmax > self.dir_max:
			self.dir_max = dmax
	
	def show_image(self):
		img = Image.fromarray(self.dataImg)
		img.show()

	def save_image(self, outfile):
		img = Image.fromarray(self.dataImg)
		img.save(outfile)

	def save_obj(self, outfile):
		with open(outfile, "w") as fout:
			fout.write("# Import Z-up, Y-forward\n")
			fout.write("g mesh\n")

			for y in range(0, self.y_max):
				for x in range(0, self.x_max):
					fout.write(f"v {x} {y} {self.data[y,x]}\n")
					
				# Connect vertices to previous row.
				if not y == 0:
					rowWidth = self.x_max
					top = -2 * rowWidth
					bottom = -rowWidth
					for x in range(0, rowWidth-1):
						fout.write(f"f {top} {top+1} {bottom}\n")
						fout.write(f"f {bottom} {top+1} {bottom+1}\n")
						top += 1
						bottom += 1

	def process_file(self, fp, base_outdirname, base_filename):
		self.load(fp)

		if self.gen_png:
			dirname = f"{base_outdirname}-png"
			if not os.path.exists(dirname):
				os.makedirs(dirname)
			outfile = os.path.join(dirname, f"{base_filename}.png")
			self.save_image(outfile)

		if self.gen_obj:
			dirname = f"{base_outdirname}-obj"
			if not os.path.exists(dirname):
				os.makedirs(dirname)
			outfile = os.path.join(dirname, f"{base_filename}.obj")
			self.save_obj(outfile)

	# Process the files directly from the .zip file.
	def process_zip(self):
		# Find the zip file with the most recent data for the specified mesh.
		dir = os.path.join("data", self.mid1, self.mid2)
		mesh_id = f"{self.mid1}{self.mid2}"
		resolution = self.mesh_type
		date = None
		for file in [x for x in Path(dir).iterdir() if x.is_file()]:
			pattern = f'FG-GML-{mesh_id}-{resolution}-(........)\\.zip'
			m = re.fullmatch(pattern, file.name)
			if m:
				dir_date = m.group(1)
				if date == None or date < dir_date:
					date = dir_date
		if not date:
			self.error(f"Unable to find the mesh zip file")
		mesh_zip_base = f"FG-GML-{mesh_id}-{resolution}-{date}"
		mesh_zip = f"{mesh_zip_base}.zip"
		outdirbase = os.path.join(dir, mesh_zip_base)

		if self.list_cells:
			cells = np.full((10, 10), False)

		# Process each .xml file in the zip file.
		path_zip = os.path.join(dir, mesh_zip)
		with zipfile.ZipFile(path_zip, "r") as z:
			for f in sorted(z.namelist()):
				(fbase, ext) = os.path.splitext(f)
				if ext == '.xml':
					pattern = f'FG-GML-{self.mid1}-{self.mid2}-(.)(.)-{resolution}-(........)'
					m = re.fullmatch(pattern, fbase)
					if m:
						y = int(m.group(1))
						x = int(m.group(2))
					else:
						error(f"Invalid xml file name in zip file: {fbase}.xml")

					if self.list_cells:
						cells[x][y] = True
					# If we're only showing one cell, filter out the others.
					elif self.mid3_set and not self.mid3_set == f"{y}{x}":
						continue
					else:
						with z.open(f) as fp:
							self.mid3 = f"{y}{x}"
							self.process_file(fp, outdirbase, fbase)
							self.mid3 = self.mid3_set

		if not self.mid3_set:
			# Print sector summary.
			print("Summary:")
			print(f"  Min height: {self.dir_min}")
			print(f"  Max height: {self.dir_max}")

		if self.list_cells:
			print(f"Cells for {self.mid1}-{self.mid2} ({self.mesh_type}):")
			for y in range(9, -1, -1):
				print("  ", end='')
				for x in range(0, 10):
					if cells[x][y]:
						print(f" {y}{x}", end='')
					else:
						print(f" --", end='')
				print()

def error(msg):
	print(f"ERROR - {msg}")
	exit()

def main():
	parser = argparse.ArgumentParser(
		description='Extract DEM data for Japan',
		usage=f"{sys.argv[0]} <mesh_id> [options]")
	parser.add_argument('mesh_id', help="6- or 8-digit mesh id")
	parser.add_argument('--png', action='store_true', help="Generate crude png thumbnails")
	parser.add_argument('--obj', action='store_true', help="Generate Wavefront .obj")
	parser.add_argument('--list', action='store_true', help="List valid cells for quadrant")
	parser.add_argument('--dem', choices=["DEM1A", "DEM5A"], default="DEM1A", help="Mesh resolution, default=DEM1A")

	parser._positionals.title = "where"
	parser._optionals.title = "and [options] are"
	args = parser.parse_args()

	dem = ProcessDEM(args)

	# Mt Fuji lat/long: 35.363410, 138.731653

	#dem.process_file("data/6041/26/FG-GML-604126-DEM1A-20251107", "FG-GML-6041-26-03-DEM1A-20250507.xml")

	#dem.process_dir("604126", "DEM1A")
	#dem.process_dir("604126", "DEM5A")
	#dem.process_zip("513461", "DEM1A")
	dem.process_zip()

if __name__ == "__main__":
	main()
