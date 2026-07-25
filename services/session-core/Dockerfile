# Session Core — Spring Boot (Java 21)
# Build context: monorepo root (plugin-sdk-java + contracts/).
# syntax=docker/dockerfile:1

FROM maven:3.9.9-eclipse-temurin-21 AS build
WORKDIR /src

# POM hierarchy first for better layer caching.
COPY pom.xml ./
COPY packages/plugin-sdk-java/pom.xml packages/plugin-sdk-java/
COPY services/session-core/pom.xml services/session-core/

# Source + contracts (schemas embutidos no jar em package).
COPY packages/plugin-sdk-java packages/plugin-sdk-java
COPY services/session-core services/session-core
COPY contracts contracts

RUN --mount=type=cache,target=/root/.m2 \
    mvn -pl services/session-core -am package -DskipTests -B \
    && cp services/session-core/target/session-core.jar /tmp/session-core.jar

FROM eclipse-temurin:21-jre-jammy
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /tmp/session-core.jar /app/session-core.jar

# Paths usados no compose (volumes).
RUN mkdir -p /data/session-core /config

ENV SERVER_PORT=8080 \
    SESSION_CORE_TRANSCRIPT_FEED_URL=ws://transcription:8001/ws/transcripts \
    SESSION_CORE_MEMORY_HUB_PATH=/data/session-core/memory-hub.db \
    SESSION_CORE_AI_PROVIDER_HUB_PATH=/config/ai-providers.yaml

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=5s --start-period=40s --retries=6 \
  CMD curl -fsS "http://127.0.0.1:${SERVER_PORT}/actuator/health" | grep -q '"status":"UP"' || exit 1

# Roda como root no compose de desenvolvimento para bind-mounts WSL
# (data/session-core, config/ai-providers.yaml) serem graváveis sem chown.

CMD ["java", "-jar", "/app/session-core.jar"]
