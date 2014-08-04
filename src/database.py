import logging
from datetime import datetime, timedelta
from time import strptime, mktime
from collections import defaultdict

from contextlib import contextmanager

from sqlalchemy import *
from sqlalchemy.orm import sessionmaker, relationship, backref, aliased
from sqlalchemy.ext.declarative import declarative_base


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
    server = relationship('Server', backref=backref('hypervisor', uselist=False), uselist=False)

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
        """Initializes a Data Access Object, utilizing an existing engine if available (otherwise it creates one)"""
        self.log = logging.getLogger("lab_monitor.database.{0}".format(self.__class__.__name__))
        self.log.info("Initializing")

        try:
            global DBENGINE
            DBENGINE
            self.log.info("Global engine is available")
        except NameError:
            self.log.info("Global engine not found, creating one")
            DBENGINE = create_engine(self.DB)
            Base.metadata.create_all(DBENGINE)
            Session.configure(bind=DBENGINE)

        self.engine = DBENGINE


class ServersDAO(DAO):

    def server_create(self, addr, type_, rack, size, position):
        """Adds a new server to monitor"""
        self.log.info("Creating a new server (%s)", addr)
        with session_scope() as session:
            session.add(Server(addr, type_, rack, size, position))

    def server_list(self, rack=None, with_health=False):
        """Returns all monitored servers as a list of dictionaries"""
        with session_scope() as session:
            data = []

            q = session.query(Server).outerjoin(Server.hypervisor).filter(Server.rack==rack if rack is not None else True)
            for serv in q:
                row = {'id':serv.id_, 'addr':serv.addr, 'type':serv.type_, 'rack':serv.rack, 'size':serv.size, 'position':serv.position, 'hypervisor':None}
                if serv.hypervisor is not None:
                    row['hypervisor'] = serv.hypervisor.addr

                if with_health:
                    try:
                        power_units = session.query(PowerUnits).filter(PowerUnits.server==serv.addr).group_by(PowerUnits.power_supply).order_by(PowerUnits.power_supply)
                        temperature = session.query(Temperature) \
                            .filter(Temperature.server==serv.addr, Temperature.sensor=='Ambient Zone') \
                            .order_by(desc(Temperature.timestamp)) \
                            .first()

                        row['power_supplies'] = [unit.health=='Ok' and unit.operational=='Ok' for unit in power_units]
                        row['temperature'] = u"{0}\u00b0".format(temperature.reading)
                    except AttributeError:
                        row['power_supplies'] = []
                        row['temperature'] = '?'

                data.append(row)

            return data

    def server_has_hypervisor(self, id_, except_for=None):
        """Checks if a given server has a corresponding ESXi hypervisor"""
        with session_scope() as session:
            q = session.query(Server).join(Server.hypervisor).filter(Server.id_==id_)
            if except_for is None:
                return q.count()
            else:
                return q.count() and q[0].hypervisor.addr!=except_for

    def server_position(self, rack, position0, position1, except_for=None):
        """Searches for servers on given place (rack number, bottom position, top position). Optionally excludes a server with given address."""
        with session_scope() as session:
            q = session.query(Server) \
                .filter(Server.rack==rack, position0<=(Server.position+Server.size-1), Server.position<=position1, Server.addr!=except_for if except_for is not None else True)
            return q.count()

    def server_delete(self, id_=None, addr=None):
        """Deletes a server by ID or address, with all readings and a corresponding ESXi hypervisor (if any)"""
        self.log.info("Deleting a server (%s)", id_ or addr)
        with session_scope() as session:
            serv = None
            try:
                if id_ is not None:
                    serv = session.query(Server).get(id_)
                elif addr is not None:
                    serv = session.query(Server).filter(Server.addr==addr)[0]

                if serv is None:
                    raise IndexError
            except IndexError:
                self.log.error("Server cannot be found")
                return

            for table in [ServerStatus, PowerUsage, PowerUnits, Temperature]:
                session.query(table).filter(table.server==serv.addr).delete()

            hyperv = session.query(Server).join(Server.hypervisor).filter(Server.id_==serv.id_).first()
            if hyperv is not None:
                session.delete(hyperv)

            session.delete(serv)

    def server_update(self, id_=None, addr=None, update={}):
        """Updates a server by ID or address"""
        self.log.info("Updating a server (%s)", id_ or addr)
        with session_scope() as session:
            serv = None
            try:
                if id_ is not None:
                    serv = session.query(Server).get(id_)
                elif addr is not None:
                    serv = session.query(Server).filter(Server.addr==addr)[0]

                if serv is None:
                    raise IndexError
            except IndexError:
                self.log.error("Server cannot be found")
                return

            for field, new in update.iteritems():
                setattr(serv, field, new)

    def hypervisor_list(self, rack=None):
        """Lists all defined ESXi hypervisors"""
        with session_scope() as session:
            data = []

            serv = aliased(Server)
            q = session.query(Hypervisor).join(serv, Hypervisor.server).filter(serv.rack==rack if rack is not None else True)
            for hyperv in q:
                row = {'addr':hyperv.addr, 'type':hyperv.type_, 'ilo_addr':hyperv.server.addr, 'rack':hyperv.server.rack}
                data.append(row)

            return data

    def hypervisor_create(self, addr, type_, server_id):
        """Creates an ESXi hypervisor"""
        self.log.info("Creating a hypervisor (%s)", addr)
        with session_scope() as session:
            session.add(Hypervisor(addr, type_, server_id))

    def hypervisor_update(self, id_=None, addr=None, update={}):
        """Updates an ESXi hypervisor by ID or address"""
        self.log.info("Updating a hypervisor (%s)", id_ or addr)
        with session_scope() as session:
            hyperv = None
            try:
                if id_ is not None:
                    hyperv = session.query(Hypervisor).get(id_)
                elif addr is not None:
                    hyperv = session.query(Hypervisor).filter(Hypervisor.addr==addr)[0]

                if hyperv is None:
                    raise IndexError
            except IndexError:
                self.log.error("Hypervisor cannot be found")
                return

            for field, new in update.iteritems():
                setattr(hyperv, field, new)

    def hypervisor_delete(self, id_=None, addr=None):
        """Deletes an ESXi hypervisor by ID or address"""
        self.log.info("Deleting a hypervisor (%s)", id_ or addr)
        with session_scope() as session:
            hyperv = None
            try:
                if id_ is not None:
                    hyperv = session.query(Hypervisor).get(id_)
                elif addr is not None:
                    hyperv = session.query(Hypervisor).filter(Hypervisor.addr==addr)[0]

                if hyperv is None:
                    raise IndexError
            except IndexError:
                self.log.error("Hypervisor cannot be found")
                return

            session.delete(hyperv)


    def get_laboratory(self):
        pass

    def get_rack(self, no):
        pass


class SensorsDAO(DAO):

    def store_server_status(self, server, status):
        """Inserts server status record to the database"""
        self.log.info("Storing server status of %s", server)
        with session_scope() as session:
            session.add(ServerStatus(server, status))

    def store_power_usage(self, server, present, average, minimum, maximum):
        """Inserts power usage record to the database"""
        self.log.info("Storing power usage of %s", server)
        with session_scope() as session:
            session.add(PowerUsage(server, present, average, minimum, maximum))

    def store_power_unit(self, server, power_supply, operational, health):
        """Inserts power unit record to the database"""
        # this is executed in a loop for each power supply, hence 'debug' level
        self.log.debug("Storing a power unit %s of %s", power_supply, server)
        with session_scope() as session:
            session.add(PowerUnits(server, power_supply, operational, health))

    def store_temperature(self, server, sensor, reading):
        """Inserts temperature sensor reading to the database"""
        self.log.debug("Storing a temperature sensor %s of %s", sensor, server) # ditto
        with session_scope() as session:
            session.add(Temperature(server, sensor, reading))

    def get_time_bounds(self, table, server):
        """Returns the earliest and the latest timestamp existing in a given table"""
        with session_scope() as session:
            q1 = session.query(table).order_by(table.timestamp)
            if q1.count():
                low = q1.first().timestamp
                q2 = session.query(table).order_by(desc(table.timestamp))
                high = q2.first().timestamp
                return self.tojstime(low), self.tojstime(high)
            return None

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
                    data[col].append([self.tojstime(row.timestamp), getattr(row, col)])

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
                data[row.power_supply].append([self.tojstime(row.timestamp), int(row.operational=='Ok' and row.health=='Ok')])

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
                data[row.sensor].append([self.tojstime(row.timestamp), row.reading])

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
                data['status'].append([self.tojstime(row.timestamp), int(row.status)])

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
                data['temperature'] = u"{0}\u00b0".format(temperature.reading)
            except:
                data['temperature'] = '?'

            try:
                data['power_usage'] = "{0} W".format(power_usage.present)
            except:
                data['power_usage'] = '?'

            try:
                data['status'] = "ok" if status.status else "alert"
            except:
                data['status'] = '?'

            return data

    def tojstime(self, timestamp):
        """Converts a datetime object to the JavaScript epoch (milliseconds since Jan 1, 1970)"""
        return 1000*mktime(timestamp.timetuple())
