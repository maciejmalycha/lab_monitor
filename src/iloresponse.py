class ILOResponse(object):
	"""
	This class parses and stores output from ILO `show` command
	"""
	def __init__(self, lines):
		self.properties = {}

		section = None

		for line in lines:
			# remove trailing newline
			line = line.rstrip()

			if line.startswith("    ") and section=="Properties":
				# data
				key,val = line[4:].split("=")
				self.properties[key] = val

			elif line.startswith("  "):
				# next section
				section = line[2:]

	def get(self, prop):
		return self.properties[prop]