from opentelemetry import context as context_api
from opentelemetry.context import attach, set_value
from inflection import underscore

from opentelemetry.instrumentation.utils import (
    _SUPPRESS_INSTRUMENTATION_KEY,
)

from opentelemetry.semconv.ai import SpanAttributes, TraceloopSpanKindValues

from opentelemetry.instrumentation.llamaindex.utils import _with_tracer_wrapper


@_with_tracer_wrapper
def workflow_wrapper(tracer, to_wrap, wrapped, instance, args, kwargs):
    """Instruments and calls every function defined in TO_WRAP."""
    if context_api.get_value(_SUPPRESS_INSTRUMENTATION_KEY):
        return wrapped(*args, **kwargs)

    name = f"llama_index_{underscore(instance.__class__.__name__)}"
    kind = to_wrap.get("kind") or TraceloopSpanKindValues.WORKFLOW.value

    attach(set_value("workflow_name", name))

    with tracer.start_as_current_span(f"{name}.workflow") as span:
        span.set_attribute(
            SpanAttributes.TRACELOOP_SPAN_KIND,
            kind,
        )
        span.set_attribute(SpanAttributes.TRACELOOP_ENTITY_NAME, name)

        return_value = wrapped(*args, **kwargs)

    return return_value
