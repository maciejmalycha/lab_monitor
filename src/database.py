from datetime import datetime

from sqlalchemy import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
Session = sessionmaker()

class Temperature(Base):
	__tablename__ = 'temperature'

	id_ = Column(Integer, primary_key=True)
	timestamp = Column(DateTime)
	server = Column(String(30))
	sensor = Column(String(30))
	reading = Column(Integer)

	def __init__(self, server, sensor, reading):
		self.timestamp = datetime.now()
		self.server = server
		self.sensor = sensor
		self.reading = reading


class SensorsDAO:
	def __init__(self, db='sqlite:///../lab_monitor.sqlite'):
		self.engine = create_engine(db)
		Base.metadata.create_all(self.engine)
		Session.configure(bind=self.engine)

	def store_power_usage(self, data):
		"""
		Inserts power usage data (from sensors.SSHiLoSensors.power_use) to the database
		"""

	def store_power_units(self, data):
		"""
		Inserts power units data (from sensors.SSHiLoSensors.power_units) to the database
		"""

	def store_temperature(self, server, sensor, reading):
		"""
		Inserts temperature sensor reads (from sensors.SSHiLoSensors.temp_sensors) to the database
		"""
		session = Session()
		try:
			t = Temperature(server, sensor, reading)
			session.add(t)
			session.commit()
		except:
			session.rollback()
			raise

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