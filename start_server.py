import os
import signal
import subprocess
import time
processes=[]
def stop(*_):
    for p in processes:
        p.terminate()
    for p in processes:
        try: p.wait(timeout=10)
        except subprocess.TimeoutExpired: p.kill()
    raise SystemExit(0)
signal.signal(signal.SIGTERM,stop)
signal.signal(signal.SIGINT,stop)
try:
    for command in [
        ['su','chattime','-s','/bin/sh','-c','exec python -m uvicorn billing:app --host 127.0.0.1 --port 8000'],
        ['su','chattime','-s','/bin/sh','-c','exec python -m streamlit run app.py --server.port=8502 --server.address=127.0.0.1'],
        ['nginx','-c','/app/nginx.conf','-g','daemon off;']]:
        processes.append(subprocess.Popen(command))
    while all(p.poll() is None for p in processes): time.sleep(1)
finally:
    stop()
