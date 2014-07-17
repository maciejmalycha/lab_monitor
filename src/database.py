from datetime import datetime

from sqlalchemy import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
Session = sessionmaker()


class ServerStatus(Base):
    __tablename__ = 'server_status'

    id_ = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    server = Column(String(30))
    status = Column(Boolean)

    def __init__(self, server, status):
        self.timestamp = datetime.now()
        self.server = server
        self.status = status


class PowerUnits(Base):
    __tablename__ = 'power_units'

    id_ = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    server = Column(String(30))
    power_supply = Column(String(30))
    operational = Column(String(30))
    health = Column(String(30))

    def __init__(self, server, power_supply, operational, health):
        self.timestamp = datetime.now()
        self.server = server
        self.power_supply = power_supply
        self.operational = operational
        self.health = health


class PowerUsage(Base):
    __tablename__ = 'power_usage'

    id_ = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    server = Column(String(30))
    present = Column(Integer)
    average = Column(Integer)
    mininum = Column(Integer)
    maximum = Column(Integer)

    def __init__(self, server, present, average, mininum, maximum):
        self.timestamp = datetime.now()
        self.server = server
        self.present = present
        self.average = average
        self.minimum = minimum
        self.maximum = maximum


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

    def insert(self, table, *args):
        """Generic insert"""
        session = Session()
        try:
            t = table(*args)
            session.add(t)
            session.commit()
        except:
            session.rollback()
            raise

    def store_power_usage(self, server, present, average, mininum, maximum):
        """Inserts power usage record to the database"""
        self.insert(PowerUsage, server, present, average, mininum, maximum)

    def store_power_units(self, server, power_supply, operational, health):
        """Inserts power unit record to the database"""
        self.insert(PowerUnits, server, power_supply, operational, health)

    def store_temperature(self, server, sensor, reading):
        """Inserts temperature sensor reading to the database"""
        self.insert(Temperature, server, sensor, reading)

    def get_power_usage(self, num=10):
        """Loads num last power usage data records from the database"""

    def get_power_units(self, num=10):
        """Loads num last power units data records from the database"""

    def get_temperature(self, num=10):
        """Loads num last temperature data records from the database"""