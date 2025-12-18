# Keycloak container with pre-built themes and realm import
# Based on: https://www.keycloak.org/server/containers
FROM quay.io/keycloak/keycloak:26.0 AS builder

# Copy the MCP realm configuration for import
COPY keycloak/realm.json /opt/keycloak/data/import/mcp-realm.json

# Build Keycloak to pre-compile themes (fixes cache hash mismatch across replicas)
RUN /opt/keycloak/bin/kc.sh build

# Production image with pre-built themes
FROM quay.io/keycloak/keycloak:26.0

# Copy built Keycloak with consistent theme cache hashes
COPY --from=builder /opt/keycloak/ /opt/keycloak/

# Expose port 8080
EXPOSE 8080

ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]

# Start in dev mode with H2 database (still uses pre-built themes)
# --proxy-headers=xforwarded tells Keycloak it's behind a reverse proxy that sets X-Forwarded-* headers
# --hostname-strict=false allows dynamic hostname resolution from proxy headers
# --http-relative-path=/auth sets the base path so Keycloak serves all content under /auth/*
# --import-realm imports the MCP realm on startup
# --import-strategy=overwrite-existing ensures realm.json changes are applied even if the realm exists
CMD ["start-dev", "--http-port=8080", "--proxy-headers=xforwarded", "--hostname-strict=false", "--http-relative-path=/auth", "--import-realm", "--import-strategy=overwrite-existing"]