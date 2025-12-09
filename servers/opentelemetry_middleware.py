import logging
import os
from urllib.parse import urlparse

from fastmcp.server.middleware import Middleware, MiddlewareContext
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.trace import Status, StatusCode


def configure_aspire_dashboard(service_name: str = "expenses-mcp"):
    """Configure OpenTelemetry to send telemetry to the Aspire standalone dashboard."""
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    parsed_endpoint = urlparse(otlp_endpoint)
    use_insecure = parsed_endpoint.scheme not in ("https", "grpcs")

    # Create resource with service name
    resource = Resource.create({"service.name": service_name})

    # Configure Tracing
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        SimpleSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint, insecure=use_insecure))
    )
    trace.set_tracer_provider(tracer_provider)

    # Configure Metrics
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=otlp_endpoint, insecure=use_insecure)
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # Configure Logging
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=otlp_endpoint, insecure=use_insecure))
    )
    set_logger_provider(logger_provider)

    # Add logging handler to send Python logs to OTLP
    root_logger = logging.getLogger()
    handler_exists = any(
        isinstance(existing, LoggingHandler)
        and getattr(existing, "logger_provider", None) is logger_provider
        for existing in root_logger.handlers
    )

    if not handler_exists:
        handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
        root_logger.addHandler(handler)


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
