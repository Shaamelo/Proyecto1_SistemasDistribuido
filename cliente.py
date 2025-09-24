import os, sys, json, urllib.request, urllib.error, grpc
import file_service_pb2 as pb2
import file_service_pb2_grpc as pb2_grpc

CHUNK_SIZE = 64 * 1024

def http_get_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"_404": True}
        raise

def discover(access_rest, file_name):
    # 1) buscar dueño
    j = http_get_json(access_rest.rstrip("/") + f"/find?name={file_name}")
    if not j.get("_404"):
        return j
    # 2) si no existe, usar peer de acceso como destino por defecto (para upload)
    h = http_get_json(access_rest.rstrip("/") + "/health")
    return {
        "file": file_name,
        "owner": h["peer"]["rest"],
        "grpc": h["peer"]["grpc"],
        "new_file": True
    }

def do_download(grpc_target, file_name):
    os.makedirs("downloads", exist_ok=True)
    out_path = os.path.join("downloads", os.path.basename(file_name))
    with grpc.insecure_channel(grpc_target) as ch:
        stub = pb2_grpc.FileServiceStub(ch)
        stream = stub.Download(pb2.FileRequest(name=file_name))
        with open(out_path, "wb") as f:
            for chunk in stream:
                if chunk.data:
                    f.write(chunk.data)
    print(f"[Download] Guardado en {out_path}")

def iter_file_chunks(local_path, remote_name):
    with open(local_path, "rb") as f:
        while True:
            data = f.read(CHUNK_SIZE)
            if not data: break
            yield pb2.FileChunk(name=remote_name, data=data)

def iter_text_chunk(text, remote_name):
    yield pb2.FileChunk(name=remote_name, data=text.encode("utf-8"))

def do_upload(grpc_target, src, remote_name):
    with grpc.insecure_channel(grpc_target) as ch:
        stub = pb2_grpc.FileServiceStub(ch)
        if os.path.exists(src):
            iterator = iter_file_chunks(src, remote_name or os.path.basename(src))
        else:
            iterator = iter_text_chunk(src, remote_name or "upload_desde_texto.txt")
        ack = stub.Upload(iterator)
        print(f"[Upload] {ack.message}  bytes={ack.bytes_received}")

def usage():
    print("Uso:")
    print("  python3 cliente.py http://127.0.0.1:5001 download <nombre_archivo>")
    print("  python3 cliente.py http://127.0.0.1:5001 upload <ruta_archivo|texto> [nombre_remoto]")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        usage()

    access_rest = sys.argv[1]
    action = sys.argv[2]

    if action == "download":
        file_name = sys.argv[3]
        print(f"[Lookup] Buscando {file_name} en {access_rest}")
        info = discover(access_rest, file_name)
        if info.get("_404"):
            print("No encontrado."); sys.exit(1)
        print(f"[Lookup] Dueño={info['owner']}  gRPC={info['grpc']}")
        do_download(info["grpc"], file_name)

    elif action == "upload":
        src = sys.argv[3]
        remote_name = sys.argv[4] if len(sys.argv) > 4 else None
        candidate = remote_name or (os.path.basename(src) if os.path.exists(src) else "upload_desde_texto.txt")
        print(f"[Lookup] Buscando destino para subir como {candidate} desde {access_rest}")
        info = discover(access_rest, candidate)
        print(f"[Lookup] Dueño={info['owner']}  gRPC={info['grpc']}")
        do_upload(info["grpc"], src, remote_name)

    else:
        usage()
