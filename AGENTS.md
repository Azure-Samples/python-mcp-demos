# Instructions for coding agents

## Adding a new azd environment variable

An azd environment variable is stored by the azd CLI for each environment. It is passed to the "azd up" command and can configure both provisioning options and application settings.

When adding new azd environment variables, update these files:

1. **infra/main.parameters.json**: Add the new parameter mapping from azd env variable to Bicep parameter
   - Use format `${ENV_VAR_NAME}` for required values
   - Use format `${ENV_VAR_NAME=default}` for optional values with defaults
   - Example: `"mcpAuthProvider": { "value": "${MCP_AUTH_PROVIDER=none}" }`

2. **infra/main.bicep**: Add the Bicep parameter declaration at the top with `@description`
   - Use `@secure()` decorator for sensitive values like passwords/secrets
   - Example: `@description('Flag to enable feature X') param useFeatureX bool = false`

3. **infra/server.bicep** (or other module): If the variable needs to be passed to a container app:
   - Add a parameter to receive the value from main.bicep
   - Add the environment variable to the appropriate `env` array (e.g., `baseEnv`, or a conditional array)
   - For secrets, add to a secrets array and reference via `secretRef`

4. **infra/main.bicep**: Pass the parameter value to the module
   - Example: `featureXEnabled: useFeatureX ? someValue : ''`

5. **infra/write_env.sh** and **infra/write_env.ps1**: If the variable should be written to `.env` for local development:
   - Add a line to echo/write the value from `azd env get-value`
   - For conditional values, wrap in an if block to only write when populated

6. **infra/main.bicep outputs**: If the value needs to be stored back in azd env after provisioning:
   - Add an output (note: `@secure()` parameters cannot be outputs)
