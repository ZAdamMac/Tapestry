# A simple HTTPS server to test the ability of Tapestry to appropriately reject a bad connection.

import http.server as hs
import ssl

httpd = hs.HTTPServer(('localhost', 49152), hs.SimpleHTTPRequestHandler)
httpd.socket = ssl.wrap_socket (httpd.socket, certfile='./badCert.pem', server_side=True)
httpd.serve_forever()