import os
import json
import grpc
from concurrent import futures

import file_service_pb2 as pb2
import file_service_pb2_grpc as pb2_grpc

CHUNK_SIZE = 64 * 1024  # 64 KB

def load_config():
    path = os.environ.get("PEER_CONFIG", "peer1/config.json")
    with open(path, "r") as f:
        cfg = json.load(f)
    # Soporta formatos antiguos o nuevos de config
    # rest/grpc pueden venir como strings ("http://127.0.0.1:5001", "127.0.0.1:6001")
    if isinstance(cfg.get("grpc"), dict):
        host = cfg["grpc"]["host"]
        port = cfg["grpc"]["port"]
    else:
        # "127.0.0.1:6001"
        host, port = cfg["grpc"].split(":")
        port = int(port)
    shared_dir = cfg.get("shared_dir") or cfg.get("shared") or "peer1/archivos_compartidos"
    os.makedirs(shared_dir, exist_ok=True)
    return host, int(port), shared_dir

class FileService(pb2_grpc.FileServiceServicer):
    def __init__(self, shared_dir):
        self.shared_dir = shared_dir

    # Cliente pide descargar un archivo -> servidor envía chunks reales
    def Download(self, request, context):
        name = os.path.basename(request.name)  # simple hardening
        path = os.path.join(self.shared_dir, name)
        if not os.path.exists(path):
            context.abort(grpc.StatusCode.NOT_FOUND, f"Archivo no existe: {name}")
        try:
            with open(path, "rb") as f:
                while True:
                    data = f.read(CHUNK_SIZE)
                    if not data:
                        break
                    yield pb2.FileChunk(name=name, data=data)
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Error al leer: {e}")

    # Cliente sube un archivo -> servidor recibe chunks y guarda en shared_dir
    def Upload(self, request_iterator, context):
        out_fh = None
        out_path = None
        total = 0
        name = None
        try:
            for chunk in request_iterator:
                if name is None:
                    name = os.path.basename(chunk.name) or "upload.bin"
                    out_path = os.path.join(self.shared_dir, name)
                    out_fh = open(out_path, "wb")
                if chunk.data:
                    out_fh.write(chunk.data)
                    total += len(chunk.data)
            if out_fh:
                out_fh.flush()
                out_fh.close()
            return pb2.UploadAck(message=f"OK: {name}", bytes_received=total)
        except Exception as e:
            if out_fh:
                out_fh.close()

            if out_path and os.path.exists(out_path): os.remove(out_path)
            context.abort(grpc.StatusCode.INTERNAL, f"Error al escribir: {e}")

def serve():
    host, port, shared_dir = load_config()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_FileServiceServicer_to_server(FileService(shared_dir), server)
    server.add_insecure_port(f"{host}:{port}")
    print(f"[gRPC] Sirviendo en {host}:{port}  (shared_dir={shared_dir})")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()

