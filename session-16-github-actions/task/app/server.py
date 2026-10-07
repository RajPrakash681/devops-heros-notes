"""HTTP API around the calculator - the thing the pipeline builds and deploys."""
import os
import socket

from flask import Flask, jsonify, request

from app.calculator import OPERATIONS, calculate

app = Flask(__name__)

# Set at image build time from the git commit (see Dockerfile and the workflow),
# so a running pod can tell you exactly which commit it is.
VERSION = os.environ.get("APP_VERSION", "dev")


@app.get("/")
def index():
    return jsonify(
        app="session16-calculator",
        version=VERSION,
        served_by=socket.gethostname(),
        operations=sorted(OPERATIONS),
        example="/calc?a=10&op=add&b=5",
    )


@app.get("/health")
def health():
    return jsonify(status="ok", version=VERSION)


@app.get("/calc")
def calc():
    try:
        a = float(request.args["a"])
        b = float(request.args["b"])
        op = request.args.get("op", "add")
        return jsonify(a=a, op=op, b=b, result=calculate(a, op, b))
    except KeyError as missing:
        return jsonify(error=f"missing query parameter {missing}"), 400
    except ValueError as err:
        return jsonify(error=str(err)), 400
