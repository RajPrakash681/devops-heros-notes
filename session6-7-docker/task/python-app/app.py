import platform
import socket

import flask
from flask import Flask

app = Flask(__name__)

PAGE = """<!doctype html>
<meta charset="utf-8">
<title>Hello from Python</title>
<style>
  body {{ margin:0; height:100vh; display:grid; place-items:center;
         font:16px/1.5 system-ui, sans-serif; background:#0b1120; color:#e2e8f0; }}
  h1 {{ margin:0 0 .4rem; font-size:2rem; color:#63b3ed; }}
  code {{ background:#1e293b; padding:.15rem .4rem; border-radius:4px; }}
</style>
<div style="text-align:center">
  <h1>Hello World from Python</h1>
  <p>Flask {flask_version} on Python {py_version}</p>
  <p>Served from container <code>{host}</code></p>
  <p>Raj Prakash &mdash; DevOps Heros session 6&ndash;7</p>
</div>"""


@app.get("/")
def index():
    return PAGE.format(
        flask_version=flask.__version__,
        py_version=platform.python_version(),
        host=socket.gethostname(),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
