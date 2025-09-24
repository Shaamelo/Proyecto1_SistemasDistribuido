import os, json
from flask import Flask, jsonify, request
import urllib.request, urllib.error

def load_config():
    path = os.environ.get("PEER_CONFIG", "peer1/config.json")
    with open(path, "r") as f:
        cfg = json.load(f)

    # REST bind (acepta "http://127.0.0.1:5001" o dict)
    if isinstance(cfg.get("rest"), dict):
        host = cfg["rest"]["host"]; port = int(cfg["rest"]["port"])
        rest_uri = f"http://{host}:{port}"
    else:
        rest_uri = cfg["rest"].replace("https://", "http://")
        host_port = rest_uri.replace("http://", "")
        host, port = host_port.split(":"); port = int(port)

    # gRPC uri (acepta string o dict)
    if isinstance(cfg.get("grpc"), dict):
        grpc_uri = f"{cfg['grpc']['host']}:{cfg['grpc']['port']}"
    else:
        grpc_uri = cfg["grpc"]

    shared_dir = cfg.get("shared_dir", "peer1/archivos_compartidos")
    os.makedirs(shared_dir, exist_ok=True)

    friend_primary = (cfg.get("friend_primary") or {}).get("rest", "")
    friend_backup  = (cfg.get("friend_backup")  or {}).get("rest", "")

    return {
        "host": host, "port": port, "self_rest": rest_uri, "self_grpc": grpc_uri,
        "shared_dir": shared_dir, "friend_primary": friend_primary, "friend_backup": friend_backup
    }

CFG = load_config()
app = Flask(__name__)

def list_files():
    out = []
    for n in os.listdir(CFG["shared_dir"]):
        p = os.path.join(CFG["shared_dir"], n)
        if os.path.isfile(p):
            out.append({"name": n, "size": os.path.getsize(p)})
    return out

def get_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=2.0) as resp:
        import json as _json
        return _json.loads(resp.read().decode("utf-8"))

@app.get("/health")
def health():
    return jsonify({"status": "ok", "peer": {"rest": CFG["self_rest"], "grpc": CFG["self_grpc"]}})

@app.get("/index")
def index():
    return jsonify({"files": list_files(), "peer": {"rest": CFG["self_rest"], "grpc": CFG["self_grpc"]}})

@app.get("/find")
def find():
    name = request.args.get("name", "")
    for f in list_files():  # local
        if f["name"] == name:
            return jsonify({"file": name, "owner": CFG["self_rest"], "grpc": CFG["self_grpc"]})
    # vecinos
    for friend in [CFG["friend_primary"], CFG["friend_backup"]]:
        if not friend: continue
        try:
            j = get_json(friend.rstrip("/") + "/index")
            for f in j.get("files", []):
                if f.get("name") == name:
                    return jsonify({"file": name, "owner": friend, "grpc": j.get("peer", {}).get("grpc", "")})
        except Exception:
            pass
    return jsonify({"error": "not_found", "file": name}), 404

if __name__ == "__main__":
    print(f"[REST] {CFG['host']}:{CFG['port']}  shared_dir={CFG['shared_dir']}")
    app.run(host=CFG["host"], port=CFG["port"], threaded=True)
