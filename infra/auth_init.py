import asyncio
import os
import random
import subprocess
import uuid

from azure.identity.aio import AzureDeveloperCliCredential
from dotenv_azd import load_azd_env
from msgraph.generated.applications.item.add_password.add_password_post_request_body import (
    AddPasswordPostRequestBody,
)
from msgraph.generated.models.api_application import ApiApplication
from msgraph.generated.models.application import Application
from msgraph.generated.models.password_credential import PasswordCredential
from msgraph.generated.models.permission_scope import PermissionScope
from msgraph.generated.models.service_principal import ServicePrincipal
from msgraph.generated.models.web_application import WebApplication
from msgraph.graph_service_client import GraphServiceClient


async def get_application(graph_client: GraphServiceClient, app_id: str) -> str | None:
    """Get an application's object ID by its client/app ID."""
    apps = await graph_client.applications.get()
    if apps and apps.value:
        for app in apps.value:
            if app.app_id == app_id:
                return app.id
    return None


def update_azd_env(name: str, val: str) -> None:
    """Update an Azure Developer CLI environment variable."""
    subprocess.run(["azd", "env", "set", name, val], check=True)


async def create_application(graph_client: GraphServiceClient, request_app: Application) -> tuple[str, str]:
    """Create an Entra ID application and its service principal."""
    app = await graph_client.applications.post(request_app)
    if app is None:
        raise ValueError("Failed to create application")
    object_id = app.id
    client_id = app.app_id
    if object_id is None or client_id is None:
        raise ValueError("Created application has no ID or client ID")

    # Create a service principal for the application
    request_principal = ServicePrincipal(app_id=client_id, display_name=app.display_name)
    await graph_client.service_principals.post(request_principal)
    return object_id, client_id


async def add_client_secret(graph_client: GraphServiceClient, app_object_id: str) -> str:
    """Add a client secret to an application."""
    request_password = AddPasswordPostRequestBody(
        password_credential=PasswordCredential(display_name="FastMCPSecret"),
    )
    password_credential = await graph_client.applications.by_application_id(app_object_id).add_password.post(
        request_password
    )
    if password_credential is None:
        raise ValueError("Failed to create client secret")
    if password_credential.secret_text is None:
        raise ValueError("Created client secret has no secret text")
    return password_credential.secret_text


def fastmcp_app_redirect_uris_update() -> Application:
    """
    Create an Application object with just redirect URIs for updating existing apps.

    This is used when we only need to update redirect URIs without touching permission scopes.
    """
    redirect_uris = [
        # Include the main redirect URI for local development
        "http://localhost:8000/auth/callback",
        # Include redirect URIs for VS Code MCP client (localhost ports and vscode.dev)
        "https://vscode.dev/redirect",
    ]
    # Add common localhost ports used by VS Code for OAuth callbacks
    for port in range(33418, 33428):
        redirect_uris.append(f"http://127.0.0.1:{port}")

    return Application(
        web=WebApplication(
            redirect_uris=redirect_uris,
        ),
    )


def fastmcp_app_registration(identifier: int) -> Application:
    """
    Create an Application object configured for FastMCP Azure OAuth.

    This creates a single app registration with:
    - Web redirect URI for OAuth callback
    - An exposed API scope for FastMCP
    - Access token version 2 (required by FastMCP)
    """
    # Include redirect URIs for VS Code MCP client (localhost ports and vscode.dev)
    redirect_uris = [
        "http://localhost:8000/auth/callback",
        "https://vscode.dev/redirect",
    ]
    # Add common localhost ports used by VS Code for OAuth callbacks
    for port in range(33418, 33428):
        redirect_uris.append(f"http://127.0.0.1:{port}")

    return Application(
        display_name=f"FastMCP Server App {identifier}",
        sign_in_audience="AzureADMyOrg",  # Single tenant - change if needed
        web=WebApplication(
            redirect_uris=redirect_uris,
        ),
        api=ApiApplication(
            oauth2_permission_scopes=[
                PermissionScope(
                    id=uuid.UUID("{" + str(uuid.uuid4()) + "}"),
                    admin_consent_display_name="Access FastMCP Server",
                    admin_consent_description="Allows access to the FastMCP server as the signed-in user.",
                    user_consent_display_name="Access FastMCP Server",
                    user_consent_description="Allow access to the FastMCP server on your behalf",
                    is_enabled=True,
                    value="mcp-access",
                    type="User",
                )
            ],
            requested_access_token_version=2,  # Required by FastMCP
        ),
    )


def update_app_with_identifier_uri(client_id: str) -> Application:
    """Update application with identifier URI after we have the client ID."""
    return Application(
        identifier_uris=[f"api://{client_id}"],
    )


async def create_or_update_fastmcp_app(graph_client: GraphServiceClient) -> None:
    """Create or update a FastMCP app registration."""
    app_id_env_var = "ENTRA_PROXY_AZURE_CLIENT_ID"
    app_secret_env_var = "ENTRA_PROXY_AZURE_CLIENT_SECRET"

    app_id = os.getenv(app_id_env_var, "no-id")
    object_id = None

    if app_id != "no-id":
        print(f"Checking if application {app_id} exists...")
        object_id = await get_application(graph_client, app_id)

    identifier = random.randint(1000, 100000)

    if object_id:
        print("Application already exists, skipping creation.")
    else:
        print("Creating new FastMCP application registration...")
        request_app = fastmcp_app_registration(identifier)
        object_id, app_id = await create_application(graph_client, request_app)
        update_azd_env(app_id_env_var, app_id)
        print(f"Created application with Client ID: {app_id}")

        # Update with identifier URI now that we have the client ID
        await graph_client.applications.by_application_id(object_id).patch(update_app_with_identifier_uri(app_id))
        print(f"Set Application ID URI to: api://{app_id}")

    # Create client secret if not already set
    client_secret = os.getenv(app_secret_env_var, "no-secret")
    if client_secret == "no-secret":
        print("Adding client secret...")
        client_secret = await add_client_secret(graph_client, object_id)
        update_azd_env(app_secret_env_var, client_secret)
        print("Client secret created and saved to environment.")


async def main():
    # Configuration - customize these as needed
    auth_tenant = os.environ["AZURE_TENANT_ID"]

    print(f"Setting up FastMCP Entra proxy authentication for tenant: {auth_tenant}")

    credential = AzureDeveloperCliCredential(tenant_id=auth_tenant)
    scopes = ["https://graph.microsoft.com/.default"]
    graph_client = GraphServiceClient(credentials=credential, scopes=scopes)

    await create_or_update_fastmcp_app(graph_client)
    print("Setup complete!")


if __name__ == "__main__":
    load_azd_env()
    asyncio.run(main())
