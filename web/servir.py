# Servir la version web en local, para probarla sin publicarla.
# Uso:  python web/servir.py  [--puerto 8080]
#
# Desde el celu, con el PC en la misma red, tambien funciona:
#    python -c "import socket;print(socket.gethostbyname(socket.gethostname()))"
# y abrir  http://<esa-IP>:8080  en el navegador del telefono.
import os
import sys
import argparse
import http.server
import socketserver

RAIZ = os.path.dirname(os.path.abspath(__file__))

class Manejador(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=RAIZ, **k)
    def log_message(self, *a):
        pass
    def end_headers(self):
        # Sin cache: al recargar se ve lo ultimo que editaste.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", type=int, default=8080)
    args = ap.parse_args()
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", args.puerto), Manejador) as s:
        print("Version web sirviendo en:")
        print("  http://localhost:%d" % args.puerto)
        print("  http://<IP-de-este-PC>:%d  (desde el celu en la misma red)" % args.puerto)
        print("Ctrl+C para cerrar.")
        try:
            s.serve_forever()
        except KeyboardInterrupt:
            print()
