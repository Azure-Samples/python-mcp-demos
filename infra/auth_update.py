"""
Post-provision script to update Azure app registration redirect URIs with deployed server URL.

This script runs after provisioning to update the FastMCP app registration with the
actual deployed server URL as a redirect URI.
"""

import asyncio
import os

from azure.identity.aio import AzureDeveloperCliCredential
from dotenv_azd import load_azd_env
from msgraph.generated.models.application import Application
from msgraph.generated.models.web_application import WebApplication
from msgraph.graph_service_client import GraphServiceClient


async def get_application(graph_client: GraphServiceClient, app_id: str) -> str | None:
    """Get an application's object ID by its client/app ID."""
    try:
        apps = await graph_client.applications.get()
        if apps and apps.value:
            for app in apps.value:
                if app.app_id == app_id:
                    return app.id
        return None
    except Exception as e:
        print(f"Error getting application: {e}")
        return None


async def get_existing_redirect_uris(graph_client: GraphServiceClient, object_id: str) -> list[str]:
    """Get existing redirect URIs from an application."""
    try:
        app = await graph_client.applications.by_application_id(object_id).get()
        if app and app.web and app.web.redirect_uris:
            return list(app.web.redirect_uris)
        return []
    except Exception as e:
        print(f"Error getting existing redirect URIs: {e}")
        return []


async def main():
    load_azd_env()

    # Check if MCP auth provider is entra_proxy
    MCP_AUTH_PROVIDER = os.getenv("MCP_AUTH_PROVIDER", "none")
    if MCP_AUTH_PROVIDER != "entra_proxy":
        print("MCP auth provider is not entra_proxy, skipping redirect URI update.")
        return

    client_id = os.environ["ENTRA_PROXY_AZURE_CLIENT_ID"]
    server_url = os.environ["ENTRA_PROXY_MCP_SERVER_BASE_URL"]
    auth_tenant = os.environ["AZURE_TENANT_ID"]

    redirect_uri = f"{server_url}/auth/callback"

    print("Updating redirect URIs for FastMCP app registration...")
    print(f"  Client ID: {client_id}")
    print(f"  Server URL: {server_url}")
    print(f"  Redirect URI: {redirect_uri}")

    credential = AzureDeveloperCliCredential(tenant_id=auth_tenant)
    scopes = ["https://graph.microsoft.com/.default"]
    graph_client = GraphServiceClient(credentials=credential, scopes=scopes)

    # Get the application object ID
    object_id = await get_application(graph_client, client_id)
    if not object_id:
        print(f"Could not find application with client ID {client_id}")
        return

    # Get existing redirect URIs and add the deployed URL
    existing_uris = await get_existing_redirect_uris(graph_client, object_id)
    print(f"  Existing redirect URIs: {len(existing_uris)}")

    # Add only the deployed server redirect URI to existing URIs
    # (local/VS Code URIs are already set by auth_init.py during preprovision)
    redirect_uris = set(existing_uris)
    redirect_uris.add(redirect_uri)

    # Update the application
    app = Application(
        web=WebApplication(
            redirect_uris=list(redirect_uris),
        ),
    )
    await graph_client.applications.by_application_id(object_id).patch(app)
    print(f"Updated redirect URIs ({len(redirect_uris)} total)")
    print("Redirect URI update complete!")


if __name__ == "__main__":
    asyncio.run(main())
