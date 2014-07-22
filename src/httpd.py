from flask import *

from database import SensorsDAO
from sensors import SSHiLoSensors
from controller import ILoController


db = SensorsDAO()
controller = None

app = Flask(__name__)
app.debug = True
subscriptions = []

@app.route('/')
def dashboard():
    servers = db.server_list()
    servers_layout = [
        [
            (0, 1, 'pl-byd-esxi10-ilo'),
            (12, 5, 'pl-byd-esxi12-ilo'),
        ],
        [],[],[],[],[],[]
    ]
    return render_template('dashboard.html', servers=servers, servers_layout=servers_layout)


@app.route('/status')
def status0():
    try:
        server = db.server_list()[0]['addr']
        return redirect(url_for('status', server=server))
    except IndexError:
        # no servers defined
        return redirect(url_for('config_servers'))

@app.route('/status/<server>')
def status(server):
    return redirect(url_for('status_temperature', server=server))

@app.route('/status/<server>/temperature')
def status_temperature(server):
    servers = db.server_list()
    return render_template('status.html', servers=servers, server=server, data_src='json_temperature')

@app.route('/status/<server>/power_usage')
def status_power_usage(server):
    servers = db.server_list()
    return render_template('status.html', servers=servers, server=server, data_src='json_power_usage')

@app.route('/status/<server>/status')
def status_status(server):
    servers = db.server_list()
    return render_template('status.html', servers=servers, server=server, data_src='')

@app.route('/status/<server>/power_units')
def status_power_units(server):
    servers = db.server_list()
    return render_template('status.html', servers=servers, server=server, data_src='')


@app.route('/config')
def config():
    return redirect(url_for('config_servers'))

@app.route('/config/servers')
def config_servers():
    servers = db.server_list()
    return render_template('config_servers.html', servers=servers)

@app.route('/config/servers/create', methods=['POST'])
def config_servers_create():
    try:
        address = request.form['address']
        type_ = request.form['type']
        rack = int(request.form['rack'])
        size = int(request.form['size'])
        position = int(request.form['position'])

        # is this host reachable?
        sensor = SSHiLoSensors(address)
        sensor.disconnect()

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
        if db.server_position(rack, position, position+size-1):
            raise ValueError("There is a server on this place")


        db.server_create(address, type_, rack, size, position)
        return redirect(url_for('config_servers'))

    except BaseException as e:
        print e
        return str(e)




@app.route('/shutdown')
def shutdown():
    return ''



@app.route('/json/server/<server>/temperature')
def json_temperature(server):
    start = request.args.get('start', None)
    end = request.args.get('end', None)
    data = db.get_temperature(server, start, end)
    return jsonify(**data)


@app.route('/json/server/<server>/power_usage')
def json_power_usage(server):
    start = request.args.get('start', None)
    end = request.args.get('end', None)
    data = db.get_power_usage(server, start, end)
    return jsonify(**data)


if __name__ == '__main__':
    app.run(host='0.0.0.0')