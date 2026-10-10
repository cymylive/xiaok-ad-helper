import subprocess, sys, os
d = os.path.dirname(os.path.abspath(__file__))
log = open(os.path.join(d, "bridge.log"), "wb")
env = dict(os.environ, PYTHONUNBUFFERED="1")
p = subprocess.Popen(
    [sys.executable, "-X", "utf8", "-u", "mouse_bridge.py"],
    cwd=d, stdout=log, stderr=subprocess.STDOUT, env=env,
    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
)
print("pid", p.pid)
