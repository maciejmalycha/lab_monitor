#-*- coding: utf-8 -*-

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
    rack = Column(Integer)
    size = Column(Integer)
    position = Column(Integer)

    def __init__(self, addr, type_, rack, size, position):
        self.addr = addr
        self.type_ = type_
        self.rack = rack
        self.size = size
        self.position = position


class Hypervisor(Base):
    __tablename__ = 'hypervisors'

    id_ = Column(Integer, primary_key=True)
    addr = Column(String(30))
    type_ = Column(String(30))
    server_id = Column(Integer, ForeignKey('servers.id_'))

    def __init__(self, addr, type_, server_id):
        self.addr = addr
        self.type_ = type_
        self.server_id = server_id



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


class DAO:
    DB = 'sqlite:///../lab_monitor.sqlite'

    def __init__(self, engine=None):
        # TODO on the piece of paper
        try:
            global DBENGINE
            DBENGINE
        except NameError:
            DBENGINE = create_engine(self.DB)
            Base.metadata.create_all(DBENGINE)
            Session.configure(bind=DBENGINE)

        self.engine = DBENGINE


class ServersDAO(DAO):

    def server_create(self, addr, type_, rack, size, position):
        """Adds a new server to monitor"""
        with session_scope() as session:
            session.add(Server(addr, type_, rack, size, position))

    def server_list(self, rack=None, with_health=False):
        """Returns all monitored servers as a list of dictionaries"""
        with session_scope() as session:

            data = []

            q = session.query(Server).filter(Server.rack==rack if rack is not None else True)
            for serv in q:
                row = {'addr':serv.addr, 'type':serv.type_, 'rack':serv.rack, 'size':serv.size, 'position':serv.position}
                if with_health:
                    try:
                        power_units = session.query(PowerUnits).filter(PowerUnits.server==serv.addr).group_by(PowerUnits.power_supply).order_by(PowerUnits.power_supply)
                        temperature = session.query(Temperature) \
                            .filter(Temperature.server==serv.addr, Temperature.sensor=='Ambient Zone') \
                            .order_by(desc(Temperature.timestamp)) \
                            .first()

                        row['power_supplies'] = [unit.health=='Ok' and unit.operational=='Ok' for unit in power_units]
                        row['temperature'] = "%u°"%temperature.reading
                    except AttributeError:
                        row['power_supplies'] = []
                        row['temperature'] = '?'

                data.append(row)

            return data

    def server_position(self, rack, position0, position1, except_for=None):
        """Searches for servers on given position"""
        with session_scope() as session:
            q = session.query(Server) \
                .filter(Server.rack==rack, position0<=(Server.position+Server.size-1), Server.position<=position1, Server.addr!=except_for if except_for is not None else True)
            return q.count()

    def server_delete(self, id_=None, addr=None):
        with session_scope() as session:
            if id_ is not None:
                serv = session.query(Server).get(id_)
            elif addr is not None:
                serv = session.query(Server).filter(Server.addr==addr)[0]

            session.delete(serv)

    def server_update(self, id_=None, addr=None, update={}):
        with session_scope() as session:
            if id_ is not None:
                serv = session.query(Server).get(id_)
            elif addr is not None:
                serv = session.query(Server).filter(Server.addr==addr)[0]

            for field, new in update.iteritems():
                setattr(serv, field, new)

    def get_laboratory(self):
        pass

    def get_rack(self, no):
        pass


class SensorsDAO(DAO):

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
        """Loads power usage data records from <start, end> range (last day by default)"""
        if end is None:
            end = datetime.now()
        if start is None:
            start = end-timedelta(days=1)

        with session_scope() as session:
            data = {'present':[], 'average':[], 'minimum':[], 'maximum':[]}

            q = session.query(PowerUsage).filter(PowerUsage.server==server, between(PowerUsage.timestamp, start, end)).order_by(PowerUsage.timestamp)
            for row in q:
                for col in data.keys():
                    data[col].append([1000*mktime(strptime(str(row.timestamp), "%Y-%m-%d %H:%M:%S.%f")), getattr(row, col)])

            return data
            

    def get_power_units(self, server, start=None, end=None):
        """Loads power units data records from <start, end> range (last day by default)"""
        if end is None:
            end = datetime.now()
        if start is None:
            start = end-timedelta(days=1)

        with session_scope() as session:
            data = defaultdict(list)

            q = session.query(PowerUnits).filter(PowerUnits.server==server, between(PowerUnits.timestamp, start, end)).order_by(PowerUnits.timestamp)
            for row in q:
                data[row.power_supply].append([1000*mktime(strptime(str(row.timestamp), "%Y-%m-%d %H:%M:%S.%f")), int(row.operational=='Ok' and row.health=='Ok')])

            return data


    def get_temperature(self, server, start=None, end=None):
        """Loads temperature data records from <start, end> range (last day by default)"""
        if end is None:
            end = datetime.now()
        if start is None:
            start = end-timedelta(days=1)

        with session_scope() as session:
            data = defaultdict(list)

            q = session.query(Temperature).filter(Temperature.server==server, between(Temperature.timestamp, start, end)).order_by(Temperature.timestamp)
            for row in q:
                # Can't we store time as Unix timestamps? This would make things simpler.
                data[row.sensor].append([1000*mktime(strptime(str(row.timestamp), "%Y-%m-%d %H:%M:%S.%f")), row.reading])

            return data

    def get_status(self, server, start=None, end=None):
        """Loads power usage data records from <start, end> range (last day by default)"""
        if end is None:
            end = datetime.now()
        if start is None:
            start = end-timedelta(days=1)

        with session_scope() as session:
            data = {'status':[]}

            q = session.query(ServerStatus).filter(ServerStatus.server==server, between(ServerStatus.timestamp, start, end)).order_by(ServerStatus.timestamp)
            for row in q:
                data['status'].append([1000*mktime(strptime(str(row.timestamp), "%Y-%m-%d %H:%M:%S.%f")), int(row.status)])

            return data

    def get_general(self, server):
        """Loads last Ambient Zone temperature reading, present power usage, power supplies and server status"""

        with session_scope() as session:
            power_units = session.query(PowerUnits).filter(PowerUnits.server==server).group_by(PowerUnits.power_supply).order_by(PowerUnits.power_supply)
            temperature = session.query(Temperature) \
                .filter(Temperature.server==server, Temperature.sensor=='Ambient Zone') \
                .order_by(desc(Temperature.timestamp)) \
                .first()
            power_usage = session.query(PowerUsage) \
                .filter(PowerUsage.server==server, PowerUsage.present!=None) \
                .order_by(desc(PowerUsage.timestamp)) \
                .first()
            status = session.query(ServerStatus) \
                .filter(ServerStatus.server==server) \
                .order_by(desc(ServerStatus.timestamp)) \
                .first()

            data = {}

            try:
                data['power_units'] = "ok" if reduce(lambda a,b: a and b, (unit.health=='Ok' and unit.operational=='Ok' for unit in power_units)) else "alert"
            except:
                data['power_units'] = '?'

            try:
                data['temperature'] = "%u°"%temperature.reading
            except:
                data['temperature'] = '?'

            try:
                data['power_usage'] = "%u W"%power_usage.present
            except:
                data['power_usage'] = '?'

            try:
                data['status'] = "ok" if status.status else "alert"
            except:
                data['status'] = '?'

            return data