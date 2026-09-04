# ---------- stage 1: build ----------
# The JDK is needed to compile. It is ~180 MB of compiler and tooling that the
# running application never uses.
FROM eclipse-temurin:21-jdk AS builder

WORKDIR /build
COPY HelloWorldServer.java ./
RUN javac -d out HelloWorldServer.java

# ---------- stage 2: runtime ----------
# Only the JRE ships. Everything from the builder stage is discarded except the
# .class files copied across explicitly.
FROM eclipse-temurin:21-jre

WORKDIR /app
COPY --from=builder /build/out ./

EXPOSE 8000
CMD ["java", "HelloWorldServer"]
