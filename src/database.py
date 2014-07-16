
import time
import sqlalchemy

class ILoDatabase:
	def __init__(self, db='sqlite:///../lab_monitor.sqlite'):
		self.engine = sqlalchemy.create_engine(db)

		meta = sqlalchemy.MetaData()
		self.power_usage = sqlalchemy.Table('power_usage', meta, autoload=True, autoload_with=self.engine)
		self.power_units = sqlalchemy.Table('power_units', meta, autoload=True, autoload_with=self.engine)
		self.temperature = sqlalchemy.Table('temperature', meta, autoload=True, autoload_with=self.engine)

	def store_power_usage(self, data):
		"""
		Inserts power usage data (from sensors.SSHiLoSensors.power_use) to the database
		"""

	def store_power_units(self, data):
		"""
		Inserts power units data (from sensors.SSHiLoSensors.power_units) to the database
		"""

	def store_temperature(self, data):
		"""
		Inserts temperature sensor reads (from sensors.SSHiLoSensors.temp_sensors) to the database
		"""

	def get_power_usage(self, num=10):
		"""
		Loads num last power usage data records from the database
		"""

	def get_power_units(self, num=10):
		"""
		Loads num last power units data records from the database
		"""

	def get_temperature(self, num=10):
		"""
		Loads num last temperature data records from the database
		"""