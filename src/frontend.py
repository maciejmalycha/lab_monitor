import datetime

from flask import *

from database import ServerStatus, PowerUsage, PowerUnits, Temperature

"""
Before running the frontend, set the following attributes:

- app.servers_dao - ServersDAO
- app.sensors_dao - SensorsDAO
- app.monitor_start - callable (async)
- app.monitor_stop - callable (async)
- app.monitor_restart - callable (async)
- app.monitor_status - callable
- app.servers_changed - callable
- app.lab - Laboratory
- app.stream - EventStream
"""

app = Flask(__name__)
#app.debug = True
app.jinja_env.filters['unsafejson'] = lambda v: json.dumps(v) # encode to JSON and escape special chars

@app.context_processor
def inject_variables():
    return {'lab': app.lab, 'len': len}

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/status')
def status0():
    try:
        server = servers = app.lab.servers.keys()[0]['addr']
        return redirect(url_for('status', server=server))
    except IndexError:
        # no servers defined
        return redirect(url_for('config_servers'))

@app.route('/status/<server>')
def status(server):
    return redirect(url_for('status_temperature', server=server))

@app.route('/status/<server>/temperature')
def status_temperature(server):
    return render_template('status.html', server=server, data_src='json_temperature')

@app.route('/status/<server>/power_usage')
def status_power_usage(server):
    return render_template('status.html', server=server, data_src='json_power_usage')

@app.route('/status/<server>/status')
def status_status(server):
    return render_template('status.html', server=server, data_src='json_status')

@app.route('/status/<server>/power_units')
def status_power_units(server):
    return render_template('status.html', server=server, data_src='json_power_units')

@app.route('/config')
def config():
    return redirect(url_for('config_servers'))

@app.route('/config/servers')
def config_servers():
    return render_template('config_servers.html')

@app.route('/config/servers/create', methods=['POST'])
def config_servers_create():
    try:
        addr = request.form['addr']
        type_ = request.form['type']
        rack = int(request.form['rack'])
        size = int(request.form['size'])
        position = int(request.form['position'])

        # are numbers OK?
        if rack not in xrange(len(app.lab.racks)):
            raise ValueError("Rack number must be between 0 and 6")
        if size not in xrange(1, 6):
            raise ValueError("Size must be between 1 and 5")
        if position not in xrange(1, 43):
            raise ValueError("Position must be between 1 and 42")

        # is anyone trying to put a 3U server on the 42nd position?
        if position + size > 43:
            raise ValueError("Server does not fit")

        # are there any other servers on this place?
        if app.servers_dao.server_position(rack, position, position+size-1):
            raise ValueError("There is a server on this place")

        # is this host reachable?
        # (it takes the most time, so it's better to check other conditions first)
        #sensor = SSHiLoSensors(addr)
        #sensor.disconnect()

        app.servers_dao.server_create(addr, type_, rack, size, position)
        app.servers_changed()
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
        if rack not in xrange(len(app.lab.racks)):
            raise ValueError("Rack number must be between 0 and 6")
        if size not in xrange(1, 6):
            raise ValueError("Size must be between 1 and 5")
        if position not in xrange(1, 43):
            raise ValueError("Position must be between 1 and 42")

        # is anyone trying to put a 3U server on the 42nd position?
        if position + size > 43:
            raise ValueError("Server does not fit")

        # are there any other servers on this place?
        if app.servers_dao.server_position(rack, position, position+size-1, addr):
            raise ValueError("There is a server on this place")


        app.servers_dao.server_update(addr=addr, update={'type_':type_, 'rack':rack, 'size':size, 'position':position})
        app.servers_changed()
        return redirect(url_for('config_servers'))

    except Exception as e:
        return jsonify(error=str(e))

@app.route('/config/servers/delete/<server>')
def config_servers_delete(server):
    try:
        app.servers_dao.server_delete(addr=server)
        app.servers_changed()
        return redirect(url_for('config_servers'))

    except Exception as e:
        return jsonify(error=str(e))


@app.route('/config/esxi')
def config_hypervisors():
    servers = app.servers_dao.server_list()
    hypervisors = app.servers_dao.hypervisor_list()
    return render_template('config_esxi.html', servers=servers, hypervisors=hypervisors)

@app.route('/config/esxi/create', methods=['POST'])
def config_hypervisors_create():
    try:
        addr = request.form['addr']
        type_ = request.form['type']
        server_id = request.form['server_id']

        if app.servers_dao.server_has_hypervisor(server_id):
            raise ValueError("Selected iLo server already has a corresponding hypervisor")

        # is this host reachable?
        # (it takes the most time, so it's better to check other conditions first)
        #hyperv = ESXiHypervisor(addr)

        app.servers_dao.hypervisor_create(addr, type_, server_id)
        app.servers_changed()
        return redirect(url_for('config_hypervisors'))

    except Exception as e:
        return jsonify(error=str(e))

@app.route('/config/esxi/update/', methods=['POST'])
def config_hypervisors_update():
    try:
        addr = request.form['addr']
        type_ = request.form['type']
        server_id = request.form['server_id']

        if app.servers_dao.server_has_hypervisor(server_id, addr):
            raise ValueError("Selected iLo server already has a different corresponding hypervisor")

        app.servers_dao.hypervisor_update(addr=addr, update={'type_':type_, 'server_id':server_id})
        app.servers_changed()
        return redirect(url_for('config_hypervisors'))

    except Exception as e:
        return jsonify(error=str(e))

@app.route('/config/esxi/delete/<hypervisor>')
def config_hypervisors_delete(hypervisor):
    try:
        app.servers_dao.hypervisor_delete(addr=hypervisor)
        app.servers_changed()
        return redirect(url_for('config_hypervisors'))

    except Exception as e:
        return jsonify(error=str(e))


@app.route('/esxi/rack/<int:rack_id>')
def esxi(rack_id=0):
    return render_template('esxi.html', rack_id=rack_id)

# danger zone
@app.route('/esxi/shutdown', methods=['POST'])
def esxi_shutdown():
    app.lab.shutdown(shutdown_timeout)
    return ' '

@app.route('/esxi/force_shutdown', methods=['POST'])
def esxi_force_shutdown():
    app.lab.force.shutdown(shutdown_timeout)
    return ' '

@app.route('/esxi/rack/<int:rack_id>/shutdown', methods=['POST'])
def esxi_shutdown_rack(rack_id):
    try:
        app.lab.racks[rack_id].shutdown(shutdown_timeout)
    except LookupError:
        return '-1'
    return ' '

@app.route('/esxi/rack/<int:rack_id>/force_shutdown', methods=['POST'])
def esxi_force_shutdown_rack(rack_id):
    try:
        app.lab.racks[rack_id].force_shutdown(shutdown_timeout)
    except LookupError:
        return '-1'
    return ' '

@app.route('/esxi/server/<server>/shutdown', methods=['POST'])
def esxi_shutdown_server(server):
    try:
        app.lab.hypervisors[server].shutdown()
    except LookupError:
        return '-1'
    return ' '

@app.route('/esxi/server/<server>/force_shutdown', methods=['POST'])
def esxi_force_shutdown_server(server):
    try:
        app.lab.hypervisors[server].force_shutdown()
    except LookupError:
        return '-1'
    return ' '

@app.route('/esxi/server/<server>/<int:vm>/shutdown', methods=['POST'])
def esxi_shutdown_vm(server, vm):
    try:
        app.lab.hypervisors[server].shutdown_vm(vm)
    except LookupError:
        return '-1'
    return ' '

@app.route('/esxi/server/<server>/<int:vm>/force_shutdown', methods=['POST'])
def esxi_force_shutdown_vm(server, vm):
    try:
        app.lab.hypervisors[server].force_shutdown_vm(vm)
    except LookupError:
        return '-1'
    return ' '
# /danger zone


@app.route("/monitor/stream")
def monitor_stream():
    return Response(app.stream.subscribe(), mimetype='text/event-stream')

@app.route("/monitor/start")
def monitor_start():
    app.monitor_start()
    return ' '

@app.route("/monitor/stop")
def monitor_stop():
    app.monitor_stop()
    return ' '

@app.route("/monitor/restart")
def monitor_restart():
    app.monitor_restart()
    return ' '

@app.route("/monitor/status")
def monitor_status():
    return app.monitor_status()

@app.route('/json/servers')
def json_servers():
    servers = app.servers_dao.server_list(with_health=True)
    return jsonify(servers=servers)

@app.route('/json/server/<server>')
def json_general(server):
    data = app.sensors_dao.get_general(server)
    return jsonify(**data)

def rq_time_bounds():
    start = request.args.get('start', None)
    end = request.args.get('end', None)
    if start is not None:
        try:
            start = datetime.fromtimestamp(int(start)/1000)
        except:
            start = None
    if end is not None:
        try:
            end = datetime.fromtimestamp(int(end)/1000)
        except:
            end = None

    return start, end

@app.route('/json/server/<server>/temperature')
def json_temperature(server):
    start, end = rq_time_bounds()
    data = app.sensors_dao.get_temperature(server, start, end)
    bounds = app.sensors_dao.get_time_bounds(Temperature, server)
    return jsonify(data=data, bounds=bounds)

@app.route('/json/server/<server>/power_usage')
def json_power_usage(server):
    start, end = rq_time_bounds()
    data = app.sensors_dao.get_power_usage(server, start, end)
    bounds = app.sensors_dao.get_time_bounds(PowerUsage, server)
    return jsonify(data=data, bounds=bounds)

@app.route('/json/server/<server>/power_units')
def json_power_units(server):
    start, end = rq_time_bounds()
    data = app.sensors_dao.get_power_units(server, start, end)
    bounds = app.sensors_dao.get_time_bounds(PowerUnits, server)
    return jsonify(data=data, bounds=bounds)

@app.route('/json/server/<server>/status')
def json_status(server):
    start, end = rq_time_bounds()
    data = app.sensors_dao.get_status(server, start, end)
    bounds = app.sensors_dao.get_time_bounds(ServerStatus, server)
    return jsonify(data=data, bounds=bounds)

@app.route('/json/esxi/rack/<int:rack_id>')
def json_esxi_rack(rack_id):
    rack = app.lab.racks[rack_id]

    vms = {}
    for server in rack.servers:
        hv = server.hypervisor
        if hv is None:
            continue
        hv_vms = []
        for vm, status in hv.status().iteritems():
            hv_vms.append({'id':vm, 'status': status, 'tools': hv.check_vmwaretools(vm)})

        vms[hv.addr] = hv_vms
    return jsonify(**vms)
