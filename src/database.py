from contextlib import contextmanager

from sqlalchemy import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from datetime import datetime, timedelta
from time import strptime, mktime
from collections import defaultdict


Base = declarative_base()
Session = sessionmaker()


@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()



class Server(Base):
    __tablename__ = 'servers'

    id_ = Column(Integer, primary_key=True)
    addr = Column(String(30))
    type_ = Column(String(30))

    def __init__(self, addr, type_):
        self.addr = addr
        self.type_ = type_



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


class PowerUsage(Base):
    __tablename__ = 'power_usage'

    id_ = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    server = Column(String(30))
    present = Column(Integer)
    average = Column(Integer)
    minimum = Column(Integer)
    maximum = Column(Integer)

    def __init__(self, server, present, average, minimum, maximum):
        self.timestamp = datetime.now()
        self.server = server
        self.present = present
        self.average = average
        self.minimum = minimum
        self.maximum = maximum


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

    def server_create(self, addr, type_):
        """Adds a new server to monitor"""
        with session_scope() as session:
            session.add(Server(addr, type_))

    def server_list(self):
        """Returns all monitored servers as a list of dictionaries"""
        with session_scope() as session:
            return [{'addr':serv.addr, 'type':serv.type_} for serv in session.query(Server)]

    def server_delete(self, id_=None, addr=None):
        with session_scope() as session:
            if id_ is not None:
                serv = session.query(Server).get(id_)
            elif addr is not None:
                serv = session.query(Server).filter(Server.addr==addr)[0]

            session.delete(serv)

    def store_server_status(self, server, status):
        """Inserts power usage record to the database"""
        with session_scope() as session:
            session.add(ServerStatus(server, status))

    def store_power_usage(self, server, present, average, minimum, maximum):
        """Inserts power usage record to the database"""
        with session_scope() as session:
            session.add(PowerUsage(server, present, average, minimum, maximum))

    def store_power_unit(self, server, power_supply, operational, health):
        """Inserts power unit record to the database"""
        with session_scope() as session:
            session.add(PowerUnits(server, power_supply, operational, health))

    def store_temperature(self, server, sensor, reading):
        """Inserts temperature sensor reading to the database"""
        with session_scope() as session:
            session.add(Temperature(server, sensor, reading))

    def get_power_usage(self, server, start=None, end=None):
        """Loads num last power usage data records from <start, end> range (last hour by default)"""
        if end is None:
            end = datetime.now()
        if start is None:
            start = end-timedelta(hours=1)

        with session_scope() as session:
            data = {'present':[], 'average':[], 'minimum':[], 'maximum':[]}

            q = session.query(PowerUsage).filter(PowerUsage.server==server, between(PowerUsage.timestamp, start, end)).order_by(PowerUsage.timestamp)
            for row in q:
                for col in data.keys():
                    data[col].append([1000*mktime(strptime(str(row.timestamp), "%Y-%m-%d %H:%M:%S.%f")), getattr(row, col)])

            return data
            

    def get_power_units(self, server, start=None, end=None):
        """Loads num last power units data records from <start, end> range (last hour by default)"""

    def get_temperature(self, server, start=None, end=None):
        """Loads temperature data records from <start, end> range (last hour by default)"""
        if end is None:
            end = datetime.now()
        if start is None:
            start = end-timedelta(hours=1)

        with session_scope() as session:
            data = defaultdict(list)

            q = session.query(Temperature).filter(Temperature.server==server, between(Temperature.timestamp, start, end)).order_by(Temperature.timestamp)
            for row in q:
                # Can't we store time as Unix timestamps? This would make things simpler.
                data[row.sensor].append([1000*mktime(strptime(str(row.timestamp), "%Y-%m-%d %H:%M:%S.%f")), row.reading])

            return data
