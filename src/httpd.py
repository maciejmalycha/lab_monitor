from flask import *

from database import SensorsDAO

db = SensorsDAO()

app = Flask(__name__)
app.debug = True

@app.route('/')
@app.route('/server/<server>')
def hello_world(server='pl-byd-esxi11-ilo'):
    return render_template('index.html', server=server)

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