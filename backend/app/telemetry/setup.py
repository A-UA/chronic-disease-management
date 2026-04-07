"""OpenTelemetry SDK 初始化（在 main.py 中调用）"""
import logging

logger = logging.getLogger(__name__)


def setup_telemetry(app):
    """初始化 OpenTelemetry 自动检测

    仅在 OTLP_ENDPOINT 配置后生效，否则跳过。
    """
    from app.base.config import settings
    if not settings.OTLP_ENDPOINT:
        logger.info("OTLP_ENDPOINT not set, telemetry disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanExporter

        provider = TracerProvider()
        exporter = OTLPSpanExporter(endpoint=settings.OTLP_ENDPOINT)
        provider.add_span_processor(BatchSpanExporter(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        logger.info("OpenTelemetry initialized: endpoint=%s", settings.OTLP_ENDPOINT)
    except ImportError:
        logger.warning("OpenTelemetry packages not installed, skipping")
