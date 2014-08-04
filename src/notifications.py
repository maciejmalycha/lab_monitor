import server

class ServerCommunicationRestoredSignal():
	def __init__(self, server_list, server_name):
		pass

class ServerCommunicationLostSignal():
	def __init__(self, server_list, server_name, datetime):
		pass

class ServerPowerRestoredSignal():
	def __init__(self, server_list, server_name):
		pass

class ServerPowerPartialLossSignal():
	def __init__(self, server_list, server_name):
		pass

class ServerTemperatureRaiseSignal():
	def __init__(self, server_list, server_name, temp_value):
		pass

class ServerTemperatureDropSignal():
	def __init__(self, server_list, server_name, temp_value):
		pass

class ServerTemperatureShutdownSignal():
	def __init__(self, server_list, server_name, temp_value):
		pass

class ServerShutdownInitSignal():
	def __init__(self, server_list, server_name):
		pass

class ServerShutdownCompletedSignal():
	def __init__(self, server_list, server_name):
		pass

class RackPowerPartialLossUPSSignal():
	def __init__(self, rack):
		pass

class RackPowerPartialLossGridSignal():
	def __init__(self, rack):
		pass

class RackPowerRestoredSignal():
	def __init__(self, rack):
		pass

class RackTemperatureRaiseSignal():
	def __init__(self, rack, temp_value):
		pass

class RackTemperatureDropSignal():
	def __init__(self, rack, temp_value):
		pass

class RackTemperatureShutdownSignal():
	def __init__(self, rack, temp_value):
		pass

class LabPowerPartialLossSignal():
	def __init__(self, timeout):
		pass

class LabPowerRestoredSignal():
	def __init__(self):
		pass

class LabTemperatureRaiseSignal():
	def __init__(self, temp_value):
		pass

class LabTemperatureDropSignal():
	def __init__(self, temp_value):
		pass

class LabTemperatureShutdownSignal():
	def __init__(self, temp_val):
		pass
