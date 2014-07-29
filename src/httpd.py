import logging, logging.handlers

from flask import *
import gevent
from gevent.wsgi import WSGIServer

from sse import EventStream
from database import *
from sensors import SSHiLoSensors
from controller import ILoController
from server import *

# configure logging
baselog = logging.getLogger('lab_monitor')
baselog.setLevel(logging.INFO)

format = logging.Formatter("%(asctime)s  %(levelname)-8s %(name)-36s %(message)s", "%H:%M:%S")

ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
ch.setFormatter(format)
baselog.addHandler(ch)

rfh = logging.handlers.TimedRotatingFileHandler('../logs/lab_monitor', 'midnight')
rfh.setLevel(logging.INFO)
rfh.setFormatter(format)
baselog.addHandler(rfh)


# set up Flask and some globals
app = Flask(__name__)
app.jinja_env.filters['unsafejson'] = lambda v: json.dumps(v) # encode to JSON and escape special chars
controller_inst = None # ILoController instance
controller_gevent = None # Greenlet that started the ILoController 
shutdown_timeout = 10

stream = EventStream()

# connect to the database
servers_dao, sensors_dao = ServersDAO(), SensorsDAO()

@app.route('/')
def dashboard():
    servers = servers_dao.server_list()
    return render_template('dashboard.html', servers=servers)

@app.route('/status')
def status0():
    try:
        server = servers_dao.server_list()[0]['addr']
        return redirect(url_for('status', server=server))
    except IndexError:
        # no servers defined
        return redirect(url_for('config_servers'))

@app.route('/status/<server>')
def status(server):
    return redirect(url_for('status_temperature', server=server))

@app.route('/status/<server>/temperature')
def status_temperature(server):
    servers = servers_dao.server_list()
    return render_template('status.html', servers=servers, server=server, data_src='json_temperature')

@app.route('/status/<server>/power_usage')
def status_power_usage(server):
    servers = servers_dao.server_list()
    return render_template('status.html', servers=servers, server=server, data_src='json_power_usage')

@app.route('/status/<server>/status')
def status_status(server):
    servers = servers_dao.server_list()
    return render_template('status.html', servers=servers, server=server, data_src='json_status')

@app.route('/status/<server>/power_units')
def status_power_units(server):
    servers = servers_dao.server_list()
    return render_template('status.html', servers=servers, server=server, data_src='json_power_units')

@app.route('/config')
def config():
    return redirect(url_for('config_servers'))

@app.route('/config/servers')
def config_servers():
    servers = servers_dao.server_list()
    return render_template('config_servers.html', servers=servers)

@app.route('/config/servers/create', methods=['POST'])
def config_servers_create():
    try:
        addr = request.form['addr']
        type_ = request.form['type']
        rack = int(request.form['rack'])
        size = int(request.form['size'])
        position = int(request.form['position'])

        # are numbers OK?
        if rack not in xrange(7):
            raise ValueError("Rack number must be between 0 and 6")
        if size not in xrange(1,6):
            raise ValueError("Size must be between 1 and 5")
        if position not in xrange(1,43):
            raise ValueError("Position must be between 1 and 42")

        # is anyone trying to put a 3U server on the 42nd position?
        if position+size>43:
            raise ValueError("Server does not fit")

        # are there any other servers on this place?
        if servers_dao.server_position(rack, position, position+size-1):
            raise ValueError("There is a server on this place")

        # is this host reachable?
        # (it takes the most time, so it's better to check other conditions first)
        sensor = SSHiLoSensors(addr)
        sensor.disconnect()

        servers_dao.server_create(addr, type_, rack, size, position)
        controller_restart()
        return redirect(url_for('config_servers'))

    except Exception as e:
        return jsonify(error=str(e))

@app.route('/config/servers/update/', methods=['POST'])
def config_servers_update():
    try:
        addr = request.form['addr']
        type_ = request.form['type']
        rack = int(request.form['rack'])
        size = int(request.form['size'])
        position = int(request.form['position'])

        # are numbers OK?
        if rack not in xrange(7):
            raise ValueError("Rack number must be between 0 and 6")
        if size not in xrange(1,6):
            raise ValueError("Size must be between 1 and 5")
        if position not in xrange(1,43):
            raise ValueError("Position must be between 1 and 42")

        # is anyone trying to put a 3U server on the 42nd position?
        if position+size>43:
            raise ValueError("Server does not fit")

        # are there any other servers on this place?
        if servers_dao.server_position(rack, position, position+size-1, addr):
            raise ValueError("There is a server on this place")


        servers_dao.server_update(addr=addr, update={'type_':type_, 'rack':rack, 'size':size, 'position':position})
        controller_restart()
        return redirect(url_for('config_servers'))

    except Exception as e:
        return jsonify(error=str(e))

@app.route('/config/servers/delete/<server>')
def config_servers_delete(server):
    try:
        servers_dao.server_delete(addr=server)
        controller_restart()
        return redirect(url_for('config_servers'))

    except Exception as e:
        return jsonify(error=str(e))


@app.route('/config/esxi')
def config_hypervisors():
    servers = servers_dao.server_list()
    hypervisors = servers_dao.hypervisor_list()
    return render_template('config_esxi.html', servers=servers, hypervisors=hypervisors)

@app.route('/config/esxi/create', methods=['POST'])
def config_hypervisors_create():
    try:
        addr = request.form['addr']
        type_ = request.form['type']
        server_id = request.form['server_id']

        print "server_id=%s"%server_id

        if servers_dao.server_has_hypervisor(server_id):
            raise ValueError("Selected iLo server already has a corresponding hypervisor")

        # is this host reachable?
        # (it takes the most time, so it's better to check other conditions first)
        hyperv = ESXiHypervisor(addr)

        servers_dao.hypervisor_create(addr, type_, server_id)
        return redirect(url_for('config_hypervisors'))

    except Exception as e:
        return jsonify(error=str(e))

@app.route('/config/esxi/update/', methods=['POST'])
def config_hypervisors_update():
    try:
        addr = request.form['addr']
        type_ = request.form['type']
        server_id = request.form['server_id']

        if servers_dao.server_has_hypervisor(server_id, addr):
            raise ValueError("Selected iLo server already has a different corresponding hypervisor")

        servers_dao.hypervisor_update(addr=addr, update={'type_':type_, 'server_id':server_id})
        return redirect(url_for('config_hypervisors'))

    except Exception as e:
        return jsonify(error=str(e))

@app.route('/config/esxi/delete/<hypervisor>')
def config_hypervisors_delete(hypervisor):
    try:
        servers_dao.hypervisor_delete(addr=hypervisor)
        controller_restart()
        return redirect(url_for('config_hypervisors'))

    except Exception as e:
        return jsonify(error=str(e))


@app.route('/esxi/rack/<int:rack_id>')
def esxi(rack_id=0):
    servers = servers_dao.server_list()
    return render_template('esxi.html', servers=servers, rack_id=rack_id)

# danger zone
@app.route('/esxi/rack/<int:rack_id>/shutdown', methods=['POST'])
def esxi_shutdown_rack(rack_id):
    rack_inst = Rack(rack_id)
    force = rack_inst.shutdown(shutdown_timeout)
    return ' '

@app.route('/esxi/rack/<int:rack_id>/force_shutdown', methods=['POST'])
def esxi_force_shutdown_rack(rack_id):
    rack_inst = Rack(rack_id)
    rack_inst.force_shutdown(shutdown_timeout)
    return ' '

@app.route('/esxi/server/<server>/shutdown', methods=['POST'])
def esxi_shutdown_server(server):
    hyperv = ESXiHypervisor(server)
    hyperv.shutdown(shutdown_timeout)
    return ' '

@app.route('/esxi/server/<server>/force_shutdown', methods=['POST'])
def esxi_force_shutdown_server(server):
    hyperv = ESXiHypervisor(server)
    hyperv.force_shutdown(shutdown_timeout)
    return ' '

@app.route('/esxi/server/<server>/<int:vm>/shutdown', methods=['POST'])
def esxi_shutdown_vm(server, vm):
    hyperv = ESXiHypervisor(server)
    hyperv.shutdown_vm(vm)
    return ' '

@app.route('/esxi/server/<server>/<int:vm>/force_shutdown', methods=['POST'])
def esxi_force_shutdown_vm(server, vm):
    hyperv = ESXiHypervisor(server)
    hyperv.force_shutdown_vm(vm)
    return ' '
# /danger zone

def cstart():
    global controller_inst
    global stream
    global servers_dao, sensors_dao
    controller_inst = ILoController()
    controller_inst.state_stream = stream
    controller_inst.servers_dao = servers_dao
    controller_inst.sensors_dao = sensors_dao
    controller_inst.start()

def cstop():
    global controller_gevent
    global controller_inst
    controller_inst.stop()
    controller_gevent.join()
    controller_inst = None

def crestart():
    global controller_gevent
    gevent.spawn(cstop).join()
    controller_gevent = gevent.spawn(cstart)


@app.route("/controller/stream")
def controller_stream():
    return Response(stream.subscribe(), mimetype="text/event-stream")

@app.route("/controller/start")
def controller_start():
    global controller_inst
    global controller_gevent
    if controller_inst is None or controller_inst.state=="off":
        controller_gevent = gevent.spawn(cstart)
        return "starting"
    return "already running"

@app.route("/controller/stop")
def controller_stop():
    global controller_inst
    if controller_inst is not None and controller_inst.state!="stopping":
        gevent.spawn(cstop)
        return "stopping"
    return "already stopped"

@app.route("/controller/restart")
def controller_restart():
    global controller_inst
    if controller_inst is not None and controller_inst.state not in ["starting...", "stopping"]:
        gevent.spawn(crestart)
        return "restarting"
    return "not started"

@app.route("/controller/status")
def controller_status():
    global controller_inst
    if controller_inst is not None:
        return controller_inst.state
    else:
        return "off"

@app.route('/shutdown')
def shutdown():
    return ''

@app.route('/json/servers')
def json_servers():
    servers = servers_dao.server_list(with_health=True)
    return jsonify(servers=servers)

@app.route('/json/server/<server>')
def json_general(server):
    data = sensors_dao.get_general(server)
    return jsonify(**data)

@app.route('/json/server/<server>/temperature')
def json_temperature(server):
    start = request.args.get('start', None)
    end = request.args.get('end', None)
    data = sensors_dao.get_temperature(server, start, end)
    return jsonify(**data)


@app.route('/json/server/<server>/power_usage')
def json_power_usage(server):
    start = request.args.get('start', None)
    end = request.args.get('end', None)
    data = sensors_dao.get_power_usage(server, start, end)
    return jsonify(**data)

@app.route('/json/server/<server>/power_units')
def json_power_units(server):
    start = request.args.get('start', None)
    end = request.args.get('end', None)
    data = sensors_dao.get_power_units(server, start, end)
    return jsonify(**data)

@app.route('/json/server/<server>/status')
def json_status(server):
    start = request.args.get('start', None)
    end = request.args.get('end', None)
    data = sensors_dao.get_status(server, start, end)
    return jsonify(**data)

@app.route('/json/esxi/rack/<rack_id>')
def json_esxi_rack(rack_id):
    rack_inst = Rack(rack_id)
    hypervisors = rack_inst.get_hypervisors_ready()

    vms = {}
    for hv in hypervisors:
        hv_vms = []
        for vm, status in hv.status().iteritems():
            hv_vms.append({'id':vm, 'status': status, 'tools': hv.check_vmwaretools(vm)})

        vms[hv.addr] = hv_vms
    return jsonify(**vms)


if __name__ == "__main__":
    wsgi_server = WSGIServer(("", 5000), app, log=None)
    try:
        wsgi_server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        if controller_inst is not None:
            cstop()


#if __name__ == '__main__':
#    app.run(host='0.0.0.0')