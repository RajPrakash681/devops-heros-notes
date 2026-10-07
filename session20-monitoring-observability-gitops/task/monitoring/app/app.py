"""orders-api: a deliberately small service that emits all three observability signals.

  metrics -> GET /metrics            (prometheus_client, scraped by Prometheus)
  logs    -> one JSON object per line on stdout (read with docker logs / kubectl logs)
  traces  -> OpenTelemetry spans, exported over OTLP/HTTP when
             OTEL_EXPORTER_OTLP_ENDPOINT is set (Jaeger in the compose stack)

Every log line for a request carries the trace_id of that request, so a log line can be
followed to its trace and back.

Endpoints:
  GET  /order          simulated order: validate -> db query -> payment (random latency,
                       ~8% of payments fail with HTTP 500)
  GET  /health         200 {"status":"ok"} or 503 once marked unhealthy
  POST /admin/health   ?state=fail|ok  flips the health flag (to demo probes and alerts)
  GET  /burn           ?seconds=N  burns one CPU core for N seconds in a background thread
  POST /alerts         Alertmanager webhook receiver: logs each alert it is sent
  GET  /metrics        Prometheus exposition format
"""
import json
import os
import random
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

SERVICE = os.getenv("SERVICE_NAME", "orders-api")
PORT = int(os.getenv("PORT", "8000"))

# ---- traces -------------------------------------------------------------------------
provider = TracerProvider(resource=Resource.create({"service.name": SERVICE}))
if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("session20.orders-api")

# ---- metrics ------------------------------------------------------------------------
REQUESTS = Counter("http_requests_total", "HTTP requests handled", ["method", "path", "status"])
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["path"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)
HEALTHY = Gauge("app_healthy", "1 when /health returns 200, 0 when it returns 503")
HEALTHY.set(1)

state = {"healthy": True}


# ---- logs ---------------------------------------------------------------------------
def log(level, msg, **fields):
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "level": level,
        "service": SERVICE,
        "msg": msg,
    }
    record.update(fields)
    print(json.dumps(record), flush=True)


def ids(span):
    ctx = span.get_span_context()
    return {"trace_id": format(ctx.trace_id, "032x"), "span_id": format(ctx.span_id, "016x")}


def burn(seconds):
    end = time.time() + seconds
    x = 0
    while time.time() < end:
        x += 1  # pure-Python busy loop: one thread == about one core (the GIL)


class Handler(BaseHTTPRequestHandler):
    server_version = "orders-api/1.0"

    def log_message(self, *args):  # silence the default access log; we log JSON ourselves
        pass

    def send(self, status, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/metrics":
            return self.send(200, generate_latest(), CONTENT_TYPE_LATEST)
        start = time.perf_counter()
        status = self.route_get(url)
        REQUESTS.labels("GET", url.path, str(status)).inc()
        LATENCY.labels(url.path).observe(time.perf_counter() - start)

    def do_POST(self):
        url = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        if url.path == "/admin/health":
            want = parse_qs(url.query).get("state", ["ok"])[0]
            state["healthy"] = want != "fail"
            HEALTHY.set(1 if state["healthy"] else 0)
            log("WARN" if want == "fail" else "INFO", "health flag changed", healthy=state["healthy"])
            status = 200
            self.send(status, {"healthy": state["healthy"]})
        elif url.path == "/alerts":
            payload = json.loads(body or b"{}")
            for a in payload.get("alerts", []):
                log(
                    "WARN" if a.get("status") == "firing" else "INFO",
                    "alert notification received",
                    alert_status=a.get("status"),
                    alertname=a.get("labels", {}).get("alertname"),
                    severity=a.get("labels", {}).get("severity"),
                    instance=a.get("labels", {}).get("instance"),
                    summary=a.get("annotations", {}).get("summary"),
                )
            status = 200
            self.send(status, {"received": len(payload.get("alerts", []))})
        else:
            status = 404
            self.send(status, {"error": "not found"})
        REQUESTS.labels("POST", url.path, str(status)).inc()

    def route_get(self, url):
        if url.path == "/health":
            if state["healthy"]:
                self.send(200, {"status": "ok", "service": SERVICE})
                return 200
            self.send(503, {"status": "unhealthy", "service": SERVICE})
            return 503
        if url.path == "/burn":
            seconds = min(float(parse_qs(url.query).get("seconds", ["60"])[0]), 600)
            threading.Thread(target=burn, args=(seconds,), daemon=True).start()
            log("WARN", "cpu burn started", seconds=seconds)
            self.send(202, {"burning_for_seconds": seconds})
            return 202
        if url.path == "/order":
            return self.order()
        self.send(404, {"error": "not found"})
        return 404

    def order(self):
        order_id = random.randint(1000, 9999)
        t0 = time.perf_counter()
        with tracer.start_as_current_span("GET /order", kind=SpanKind.SERVER) as root:
            root.set_attribute("http.request.method", "GET")
            root.set_attribute("url.path", "/order")
            root.set_attribute("order.id", order_id)
            with tracer.start_as_current_span("validate_order"):
                time.sleep(random.uniform(0.005, 0.015))
            with tracer.start_as_current_span("db.query", kind=SpanKind.CLIENT) as db:
                db.set_attribute("db.system", "postgresql")
                db.set_attribute("db.query.text", "SELECT * FROM orders WHERE id = $1")
                slow = random.random() < 0.10
                time.sleep(random.uniform(0.4, 0.7) if slow else random.uniform(0.02, 0.08))
            with tracer.start_as_current_span("payment.charge", kind=SpanKind.CLIENT) as pay:
                time.sleep(random.uniform(0.03, 0.08))
                failed = random.random() < 0.08
                if failed:
                    pay.set_status(Status(StatusCode.ERROR, "upstream timeout"))
            status = 500 if failed else 200
            root.set_attribute("http.response.status_code", status)
            if failed:
                root.set_status(Status(StatusCode.ERROR))
            duration_ms = round((time.perf_counter() - t0) * 1000, 1)
            if failed:
                log("ERROR", "payment failed: upstream timeout", order_id=order_id,
                    status=status, duration_ms=duration_ms, **ids(root))
                self.send(500, {"order_id": order_id, "error": "payment failed"})
            else:
                log("INFO", "order processed", order_id=order_id, status=status,
                    duration_ms=duration_ms, slow_db=slow, **ids(root))
                self.send(200, {"order_id": order_id, "status": "confirmed"})
        return status


if __name__ == "__main__":
    log("INFO", "starting", port=PORT,
        tracing=bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")))
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
