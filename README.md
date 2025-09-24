# Proyecto 1 - Sistemas Distribuidos #

## Implementación de un sistema peer-to-peer (P2P) con microservicios REST y gRPC para localización y transferencia de archivos. ##

**Descripción**

El sistema consiste en una red P2P no estructurada donde cada peer puede actuar como cliente y servidor. REST se usa para la localización de archivos y el estado de los peers.gRPC se usa para la transferencia de archivos (descarga y subida). Cada peer se configura mediante un archivo JSON que define sus puertos, directorios y peers vecinos.

**Requisitos**

Python 3.12 (probado en Google Cloud Shell).

**Librerías:**

pip install flask grpcio grpcio-tools


**Estructura de carpetas**
Proyecto1_SistemasDistribuidos/
│
├── cliente.py
├── rest_peer.py
├── grpc_server.py
├── file_service.proto
├── file_service_pb2.py
├── file_service_pb2_grpc.py
│
├── peer1/
│   ├── config.json
│   └── archivos_compartidos/
│
├── peer2/
│   ├── config.json
│   └── archivos_compartidos/ (ejemplo: hola_peer2.txt)
│
├── peer3/
│   ├── config.json
│   └── archivos_compartidos/ (ejemplo: hola_peer3.txt)
│
└── logs/


**Configuración de los peers**

Cada peer tiene un archivo config.json. Ejemplo:

{
  "rest": {"host": "127.0.0.1", "port": 5002},
  "grpc": {"host": "127.0.0.1", "port": 6002},
  "shared_dir": "peer2/archivos_compartidos",
  "self_uri": {"rest": "http://127.0.0.1:5002", "grpc": "127.0.0.1:6002"},
  "friend_primary": {"rest": "http://127.0.0.1:5001"},
  "friend_backup": {"rest": "http://127.0.0.1:5003"}
}

**Ejecución de los peers**

En tres terminales distintas, ejecutar:

export PEER_CONFIG=peer1/config.json
nohup python3 rest_peer.py > logs/p1_rest.log 2>&1 &
nohup python3 grpc_server.py > logs/p1_grpc.log 2>&1 &

export PEER_CONFIG=peer2/config.json
nohup python3 rest_peer.py > logs/p2_rest.log 2>&1 &
nohup python3 grpc_server.py > logs/p2_grpc.log 2>&1 &

export PEER_CONFIG=peer3/config.json
nohup python3 rest_peer.py > logs/p3_rest.log 2>&1 &
nohup python3 grpc_server.py > logs/p3_grpc.log 2>&1 &

**Pruebas**
1. Verificar estado de un peer
curl http://127.0.0.1:5001/health

2. Listar archivos de un peer
curl http://127.0.0.1:5002/index

3. Buscar archivo en la red
curl "http://127.0.0.1:5001/find?name=hola_peer2.txt"

4. Descargar un archivo con el cliente
python3 cliente.py http://127.0.0.1:5001 download hola_peer2.txt

*El archivo descargado queda en la carpeta downloads/.*

5. Subir un archivo con el cliente
echo "contenido desde el cliente" > prueba_cliente.txt
python3 cliente.py http://127.0.0.1:5001 upload ./prueba_cliente.txt

6. Concurrencia

Ejecutar varias consultas simultáneas al peer:

seq 1 10 | xargs -n1 -P10 -I{} curl -s "http://127.0.0.1:5001/find?name=hola_peer2.txt" >/dev/null
echo "Concurrencia OK"

**Notas:**
- Peer1 actúa como punto de acceso inicial, aunque cualquier peer puede serlo.
- Si un peer se cae, la consulta se puede redirigir a los peers vecinos definidos en el config.json.
- Las operaciones de transferencia usan servicios gRPC de tipo ECO: el archivo no se transfiere realmente, pero se confirma la operación devolviendo mensajes de control.
