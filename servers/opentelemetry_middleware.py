import json
import logging
import os
from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler  # _logs is "experimental", not "private"
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.util.types import AttributeValue


def configure_aspire_dashboard(service_name: str = "expenses-mcp"):
    """Configure OpenTelemetry to send telemetry to the Aspire standalone dashboard.

    Requires the OTEL_EXPORTER_OTLP_ENDPOINT environment variable to be set.
    """
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otlp_endpoint:
        raise ValueError("OTEL_EXPORTER_OTLP_ENDPOINT environment variable must be set to configure telemetry export.")

    # Create resource with service name
    resource = Resource.create({"service.name": service_name})

    # Configure Tracing
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
    trace.set_tracer_provider(tracer_provider)

    # Configure Metrics
    metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=otlp_endpoint))
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # Configure Logging
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter(endpoint=otlp_endpoint)))
    set_logger_provider(logger_provider)

    # Add logging handler to send Python logs to OTLP
    root_logger = logging.getLogger()
    handler_exists = any(
        isinstance(existing, LoggingHandler) and getattr(existing, "logger_provider", None) is logger_provider
        for existing in root_logger.handlers
    )

    if not handler_exists:
        handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
        root_logger.addHandler(handler)


class OpenTelemetryMiddleware(Middleware):
    """Middleware that creates OpenTelemetry spans for MCP operations."""

    def __init__(self, tracer_name: str):
        self.tracer = trace.get_tracer(tracer_name)

    def _span_name(self, method_name: str, target: str | None) -> str:
        if target:
            return f"{method_name} {target}"
        return method_name

    def _safe_json_str(self, value: Any) -> str | None:
        """Best-effort JSON serialization.

        `gen_ai.tool.call.arguments` is semconv opt-in and may be sensitive.
        The OTEL Python SDK span attribute type system doesn't support
        arbitrary nested objects, so we encode as a JSON string.
        """
        if value is None:
            return None
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            return str(value)

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """Create a span for each tool call following MCP semantic conventions."""
        # MCP semconv: span name is "{mcp.method.name} {target}" where target matches gen_ai.tool.name.
        method_name = str(getattr(context, "method", "")) or "tools/call"
        tool_name = str(getattr(context.message, "name", "")) or "unknown"
        span_name = self._span_name(method_name=method_name, target=tool_name)

        attributes: dict[str, AttributeValue] = {
            "mcp.method.name": method_name,
            # PR #2083 aligns tool/prompt naming with GenAI attributes.
            "gen_ai.tool.name": tool_name,
            "gen_ai.operation.name": "execute_tool",
        }

        # Opt-in sensitive attribute (kept for backwards compatibility with prior behavior,
        # but now recorded under the semconv key).
        tool_args_json = self._safe_json_str(getattr(context.message, "arguments", None))
        if tool_args_json is not None:
            attributes["gen_ai.tool.call.arguments"] = tool_args_json

        with self.tracer.start_as_current_span(span_name, attributes=attributes) as span:
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

        method_name = str(getattr(context, "method", "")) or "resources/read"
        span_name = self._span_name(method_name=method_name, target=resource_uri if resource_uri != "unknown" else None)

        with self.tracer.start_as_current_span(
            span_name,
            attributes={
                "mcp.method.name": method_name,
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

        method_name = str(getattr(context, "method", "")) or "prompts/get"
        span_name = self._span_name(method_name=method_name, target=prompt_name if prompt_name != "unknown" else None)

        with self.tracer.start_as_current_span(
            span_name,
            attributes={
                "mcp.method.name": method_name,
                "gen_ai.prompt.name": str(prompt_name),
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
