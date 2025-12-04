from fastmcp.server.middleware import Middleware, MiddlewareContext
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


class OpenTelemetryMiddleware(Middleware):
    """Middleware that creates OpenTelemetry spans for MCP operations."""

    def __init__(self, tracer_name: str):
        self.tracer = trace.get_tracer(tracer_name)

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """Create a span for each tool call with detailed attributes."""
        tool_name = context.message.name

        with self.tracer.start_as_current_span(
            f"tool.{tool_name}",
            attributes={
                "mcp.method": context.method,
                "mcp.source": context.source,
                "mcp.tool.name": tool_name,
                # If arguments are sensitive, consider omitting or sanitizing them
                # If arguments are long/nested, consider adding a size or depth limit
                "mcp.tool.arguments": str(context.message.arguments),
            },
        ) as span:
            try:
                result = await call_next(context)
                span.set_attribute("mcp.tool.success", True)
                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                span.set_attribute("mcp.tool.success", False)
                span.set_attribute("mcp.tool.error", str(e))
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    async def on_read_resource(self, context: MiddlewareContext, call_next):
        """Create a span for each resource read."""
        resource_uri = str(getattr(context.message, "uri", "unknown"))

        with self.tracer.start_as_current_span(
            f"resource.{resource_uri}",
            attributes={
                "mcp.method": context.method,
                "mcp.source": context.source,
                "mcp.resource.uri": resource_uri,
            },
        ) as span:
            try:
                result = await call_next(context)
                span.set_attribute("mcp.resource.success", True)
                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                span.set_attribute("mcp.resource.success", False)
                span.set_attribute("mcp.resource.error", str(e))
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    async def on_get_prompt(self, context: MiddlewareContext, call_next):
        """Create a span for each prompt retrieval."""
        prompt_name = getattr(context.message, "name", "unknown")

        with self.tracer.start_as_current_span(
            f"prompt.{prompt_name}",
            attributes={
                "mcp.method": context.method,
                "mcp.source": context.source,
                "mcp.prompt.name": prompt_name,
            },
        ) as span:
            try:
                result = await call_next(context)
                span.set_attribute("mcp.prompt.success", True)
                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                span.set_attribute("mcp.prompt.success", False)
                span.set_attribute("mcp.prompt.error", str(e))
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
