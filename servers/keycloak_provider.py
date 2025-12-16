"""Keycloak authentication provider for FastMCP.

This module provides KeycloakAuthProvider - a complete authentication solution
that integrates with Keycloak's OAuth 2.1 and OpenID Connect services, supporting
Dynamic Client Registration (DCR) for seamless MCP client authentication.

This is based on proposed FastMCP PR:
https://github.com/jlowin/fastmcp/pull/1937


"""

from __future__ import annotations

import base64
import json

import httpx
from fastmcp.server.auth import RemoteAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.utilities.logging import get_logger
from pydantic import AnyHttpUrl
from starlette.responses import JSONResponse
from starlette.routing import Route


def decode_jwt_debug(token):
    """Decode JWT payload for debugging"""
    try:
        parts = token.split(".")
        payload = parts[1]
        payload += "=" * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        return {"error": str(e)}


logger = get_logger(__name__)


class KeycloakAuthProvider(RemoteAuthProvider):
    """Keycloak authentication provider with minimal DCR proxy for MCP compatibility.

    This provider integrates FastMCP with Keycloak using a **minimal proxy architecture**
    that solves a specific MCP compatibility issue. The proxy only intercepts DCR
    responses to fix a single field - all other OAuth operations go directly to Keycloak.

    ## Why a Minimal Proxy is Needed

    Keycloak has a known limitation with Dynamic Client Registration: it ignores
    the client's requested `token_endpoint_auth_method` parameter and always returns
    `client_secret_basic`, even when clients explicitly request `client_secret_post`
    (which MCP requires per RFC 9110).

    This minimal proxy works around this by:
    1. Advertising itself as the authorization server to MCP clients
    2. Forwarding Keycloak's OAuth metadata with a custom registration endpoint
    3. Intercepting DCR responses from Keycloak and fixing only the
       `token_endpoint_auth_method` field

    **What the minimal proxy does NOT intercept:**
    - Authorization flows (users authenticate directly with Keycloak)
    - Token issuance (tokens come directly from Keycloak)
    - Token validation (JWT signatures verified against Keycloak's keys)

    ## Setup Requirements

    1. Configure Keycloak realm with Dynamic Client Registration enabled
    2. Configure trusted hosts policy to allow client redirect URIs
    3. Set `client-uris-must-match` to `false` for dynamic redirect URIs
    4. Add test users to the realm for authentication

    Example:
        ```python
        from fastmcp import FastMCP
        from keycloak_provider import KeycloakAuthProvider

        # Create Keycloak provider (JWT verifier created automatically)
        keycloak_auth = KeycloakAuthProvider(
            realm_url="http://localhost:8080/realms/mcp",
            base_url="http://localhost:8000",
            required_scopes=["openid", "mcp:tools"],
            audience="http://localhost:8000",  # Should match Keycloak's audience mapper
        )

        # Use with FastMCP
        mcp = FastMCP("My App", auth=keycloak_auth)
        ```
    """

    def __init__(
        self,
        *,
        realm_url: str | AnyHttpUrl,
        base_url: str | AnyHttpUrl,
        required_scopes: list[str] | None = None,
        audience: str | list[str] | None = None,
        token_verifier: JWTVerifier | None = None,
    ):
        """Initialize the Keycloak authentication provider.

        Args:
            realm_url: Full URL to the Keycloak realm (e.g.,
                "https://keycloak.example.com/realms/myrealm")
            base_url: Public URL of this FastMCP server
            required_scopes: Optional list of scopes to require for all requests
            audience: Optional audience(s) for JWT validation. If not specified
                and no custom verifier is provided, audience validation is disabled.
                For production use, it's recommended to set this to your resource
                server identifier or base_url.
            token_verifier: Optional token verifier. If None, creates JWT verifier
                for Keycloak
        """
        self.base_url = AnyHttpUrl(str(base_url).rstrip("/"))
        self.realm_url = str(realm_url).rstrip("/")

        # Create default JWT verifier if none provided
        if token_verifier is None:
            # Keycloak uses specific URL patterns (not the standard .well-known paths)
            token_verifier = JWTVerifier(
                jwks_uri=f"{self.realm_url}/protocol/openid-connect/certs",
                issuer=self.realm_url,
                algorithm="RS256",
                required_scopes=required_scopes,
                audience=audience,
            )

        # Initialize RemoteAuthProvider with FastMCP as the authorization server
        # We advertise ourselves as the auth server because we provide the
        # authorization server metadata endpoint that forwards from Keycloak
        # with our /register DCR proxy endpoint.
        super().__init__(
            token_verifier=token_verifier,
            authorization_servers=[self.base_url],
            base_url=self.base_url,
        )

    def get_routes(
        self,
        mcp_path: str | None = None,
    ) -> list[Route]:
        """Get OAuth routes including Keycloak metadata forwarding and minimal DCR proxy.

        Adds two routes to the parent class's protected resource metadata:
        1. `/.well-known/oauth-authorization-server` - Forwards Keycloak's OAuth metadata
           with the registration endpoint rewritten to point to our minimal DCR proxy
        2. `/register` - Minimal DCR proxy that forwards requests to Keycloak and fixes
           only the `token_endpoint_auth_method` field in responses

        Args:
            mcp_path: The path where the MCP endpoint is mounted (e.g., "/mcp")
        """
        # Get the standard protected resource routes from RemoteAuthProvider
        routes = super().get_routes(mcp_path)

        async def oauth_authorization_server_metadata(request):
            """Forward Keycloak's OAuth metadata with registration endpoint pointing to our minimal DCR proxy."""
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.realm_url}/.well-known/oauth-authorization-server")
                    response.raise_for_status()
                    metadata = response.json()

                    # Override registration_endpoint to use our minimal DCR proxy
                    base_url = str(self.base_url).rstrip("/")
                    metadata["registration_endpoint"] = f"{base_url}/register"

                    # Override issuer to match our base URL (required for OAuth discovery)
                    # VS Code validates that the issuer matches the authorization server URL
                    # AnyHttpUrl adds trailing slash to root URLs, so we need to match that

                    # Also fix mtls_endpoint_aliases if present (VS Code may check this)
                    if "mtls_endpoint_aliases" in metadata:
                        metadata["mtls_endpoint_aliases"]["registration_endpoint"] = f"{base_url}/register"

                    return JSONResponse(metadata)
            except Exception as e:
                logger.error(f"Failed to fetch Keycloak metadata: {e}")
                return JSONResponse(
                    {
                        "error": "server_error",
                        "error_description": f"Failed to fetch Keycloak metadata: {e}",
                    },
                    status_code=500,
                )

        # Add Keycloak authorization server metadata forwarding
        routes.append(
            Route(
                "/.well-known/oauth-authorization-server",
                endpoint=oauth_authorization_server_metadata,
                methods=["GET"],
            )
        )

        async def register_client_fix_auth_method(request):
            """Minimal DCR proxy that fixes token_endpoint_auth_method in Keycloak's client registration response.

            Forwards registration requests to Keycloak's DCR endpoint and modifies only the
            token_endpoint_auth_method field in the response. For MCP compatibility:
            - "client_secret_basic" -> "none" (public client, no secret needed)
            - Preserves "none" if requested

            All other fields are passed through unchanged.
            """
            try:
                body = await request.body()

                # Log incoming request for debugging
                try:
                    import json

                    request_data = json.loads(body)
                    logger.info(
                        f"DCR request received: client_name={request_data.get('client_name')}, "
                        f"redirect_uris={request_data.get('redirect_uris')}, "
                        f"token_endpoint_auth_method={request_data.get('token_endpoint_auth_method')}"
                    )
                except Exception:
                    logger.info(f"DCR request received (raw): {body[:500]}")

                # Forward to Keycloak's DCR endpoint
                async with httpx.AsyncClient(timeout=10.0) as client:
                    forward_headers = {
                        key: value
                        for key, value in request.headers.items()
                        if key.lower() not in {"host", "content-length", "transfer-encoding", "content-type"}
                    }
                    forward_headers["Content-Type"] = "application/json"

                    # Keycloak's standard DCR endpoint pattern
                    registration_endpoint = f"{self.realm_url}/clients-registrations/openid-connect"

                    logger.info(f"Forwarding DCR to Keycloak: {registration_endpoint}")

                    response = await client.post(
                        registration_endpoint,
                        content=body,
                        headers=forward_headers,
                    )

                    logger.info(f"Keycloak DCR response status: {response.status_code}")

                    if response.status_code != 201:
                        error_body = response.text
                        logger.error(f"Keycloak DCR failed: {response.status_code} - {error_body}")
                        try:
                            error_json = response.json()
                        except Exception:
                            error_json = {"error": "registration_failed", "error_description": error_body}
                        return JSONResponse(
                            error_json,
                            status_code=response.status_code,
                        )

                    # Fix token_endpoint_auth_method for MCP compatibility
                    client_info = response.json()
                    original_auth_method = client_info.get("token_endpoint_auth_method")

                    logger.info(f"Keycloak returned token_endpoint_auth_method: {original_auth_method}")

                    # MCP requires public clients (token_endpoint_auth_method: none)
                    # Keycloak ignores the client's request and returns client_secret_basic
                    # We fix this by always returning "none" for MCP clients
                    if original_auth_method in ("client_secret_basic", "client_secret_post"):
                        logger.info(f"Fixing token_endpoint_auth_method: {original_auth_method} -> none")
                        client_info["token_endpoint_auth_method"] = "none"

                    logger.info(
                        f"Returning to client: client_id={client_info.get('client_id')}, "
                        f"token_endpoint_auth_method={client_info.get('token_endpoint_auth_method')}"
                    )

                    return JSONResponse(client_info, status_code=201)

            except Exception as e:
                logger.error(f"DCR proxy error: {e}")
                return JSONResponse(
                    {
                        "error": "server_error",
                        "error_description": f"Client registration failed: {e}",
                    },
                    status_code=500,
                )

        # Add minimal DCR proxy
        routes.append(
            Route(
                "/register",
                endpoint=register_client_fix_auth_method,
                methods=["POST"],
            )
        )

        async def debug_token(request):
            """Debug endpoint to decode and inspect JWT tokens"""
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return JSONResponse({"error": "No bearer token"}, status_code=400)

            token = auth_header[7:]
            claims = decode_jwt_debug(token)

            return JSONResponse(
                {
                    "token_claims": claims,
                    "expected_issuer": self.realm_url,
                    "expected_audience": str(self.base_url),
                }
            )

        routes.append(Route("/debug-token", endpoint=debug_token, methods=["GET", "POST"]))

        return routes
