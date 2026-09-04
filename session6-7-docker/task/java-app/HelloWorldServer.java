import com.sun.net.httpserver.HttpServer;

import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;

/** Smallest useful HTTP server the JDK can give you - no framework, no dependencies. */
public class HelloWorldServer {

    private static final int PORT = 8000;

    public static void main(String[] args) throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("0.0.0.0", PORT), 0);

        server.createContext("/", exchange -> {
            String body = """
                    <!doctype html>
                    <meta charset="utf-8">
                    <title>Hello from Java</title>
                    <style>
                      body { margin:0; height:100vh; display:grid; place-items:center;
                             font:16px/1.5 system-ui, sans-serif; background:#0b1120; color:#e2e8f0; }
                      h1 { margin:0 0 .4rem; font-size:2rem; color:#fc8181; }
                      code { background:#1e293b; padding:.15rem .4rem; border-radius:4px; }
                    </style>
                    <div style="text-align:center">
                      <h1>Hello World from Java</h1>
                      <p>JDK HttpServer on Java %s</p>
                      <p>Served from container <code>%s</code></p>
                      <p>Raj Prakash &mdash; DevOps Heros session 6&ndash;7</p>
                    </div>
                    """.formatted(
                            System.getProperty("java.version"),
                            InetAddress.getLocalHost().getHostName());

            byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "text/html; charset=utf-8");
            exchange.sendResponseHeaders(200, bytes.length);
            try (OutputStream out = exchange.getResponseBody()) {
                out.write(bytes);
            }
        });

        server.start();
        System.out.println("java-app listening on " + PORT);
    }
}
