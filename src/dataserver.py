import SimpleHTTPServer
import SocketServer
from database import SensorsDAO
import json
from urlparse import parse_qs

"""Prototype of a web server."""


class Handler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    """
    HTTP request handler for temperature data
    Request /[server]/temperature/?sensor=[sensor] to get data in JSON
    Request / to see the chart
    Powered by Highstock
    """

    def do_GET(self):
        """Respond to a GET request."""

        path = self.path[1:].split('/')

        try:
            (things,qs) = self.path.split('?')
            params = parse_qs(qs)
        except:
            params = {}


        db = self.server.db

        try:
            server = path[0]
            print "server='%s'"%server

            if path[1] == 'temperature':
                print "loading temp"
                data = db.get_temperature(server)

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()

                try:
                    self.wfile.write(json.dumps(data[params['sensor'][0]]))
                except KeyError:
                    self.wfile.write(json.dumps(data.keys()))

                return
        except:

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            index = open('index.html').read()
            index = index.replace('{PORT}', str(self.server.server_address[1]))

            self.wfile.write(index)
        
port = 8000

# after hitting ^C the port is still blocked; this strange fragment will find first working port
while True:
    try:
        httpd = SocketServer.TCPServer(("", port), Handler)
        break
    except:
        port+=1

httpd.db = SensorsDAO()

print "serving at port", port
httpd.serve_forever()