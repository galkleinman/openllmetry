import os
import sys
from deprecated import deprecated
import requests
from pathlib import Path

from typing import Optional
from colorama import Fore
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter
from opentelemetry.propagators.textmap import TextMapPropagator
from opentelemetry.util.re import parse_env_headers

from traceloop.sdk.telemetry import Telemetry
from traceloop.sdk.config import (
    is_content_tracing_enabled,
    is_tracing_enabled,
)
from traceloop.sdk.fetcher import Fetcher
from traceloop.sdk.tracing.tracing import (
    TracerWrapper,
    set_association_properties,
    set_correlation_id,
)
from typing import Dict


class Traceloop:
    AUTO_CREATED_KEY_PATH = str(
        Path.home() / ".cache" / "traceloop" / "auto_created_key"
    )
    AUTO_CREATED_URL = str(Path.home() / ".cache" / "traceloop" / "auto_created_url")

    __tracer_wrapper: TracerWrapper

    @staticmethod
    def init(
        app_name: Optional[str] = sys.argv[0],
        api_endpoint: str = "https://api.traceloop.com",
        api_key: str = None,
        headers: Dict[str, str] = {},
        disable_batch=False,
        exporter: SpanExporter = None,
        processor: SpanProcessor = None,
        propagator: TextMapPropagator = None,
        traceloop_sync_enabled: bool = True,
    ) -> None:
        Telemetry()

        api_endpoint = os.getenv("TRACELOOP_BASE_URL") or api_endpoint
        api_key = os.getenv("TRACELOOP_API_KEY") or api_key

        if (
            traceloop_sync_enabled
            and api_endpoint.find("traceloop.com") != -1
            and api_key
            and not exporter
            and not processor
        ):
            Fetcher(base_url=api_endpoint, api_key=api_key).run()
            print(
                Fore.GREEN + "Traceloop syncing configuration and prompts" + Fore.RESET
            )

        if not is_tracing_enabled():
            print(Fore.YELLOW + "Tracing is disabled" + Fore.RESET)
            return

        enable_content_tracing = is_content_tracing_enabled()

        if exporter or processor:
            print(Fore.GREEN + "Traceloop exporting traces to a custom exporter")

        headers = os.getenv("TRACELOOP_HEADERS") or headers

        if isinstance(headers, str):
            headers = parse_env_headers(headers)

        # auto-create a dashboard on Traceloop if no export endpoint is provided
        if (
            not exporter
            and not processor
            and api_endpoint == "https://api.traceloop.com"
            and not api_key
        ):
            headers = None  # disable headers if we're auto-creating a dashboard
            if not os.path.exists(Traceloop.AUTO_CREATED_KEY_PATH):
                os.makedirs(
                    os.path.dirname(Traceloop.AUTO_CREATED_KEY_PATH), exist_ok=True
                )
                os.makedirs(os.path.dirname(Traceloop.AUTO_CREATED_URL), exist_ok=True)

                print(
                    Fore.YELLOW
                    + "No Traceloop API key provided, auto-creating a dashboard on Traceloop",
                )
                res = requests.post(
                    "https://app.traceloop.com/api/registration/auto-create"
                ).json()
                access_url = f"https://app.traceloop.com/trace?skt={res['uiAccessKey']}"
                api_key = res["apiKey"]

                print(Fore.YELLOW + "TRACELOOP_API_KEY=", api_key)

                open(Traceloop.AUTO_CREATED_KEY_PATH, "w").write(api_key)
                open(Traceloop.AUTO_CREATED_URL, "w").write(access_url)
            else:
                api_key = open("/tmp/traceloop_key.txt").read()
                access_url = open("/tmp/traceloop_url.txt").read()

            print(
                Fore.GREEN + f"\nGo to {access_url} to see a live dashboard\n",
            )

        if not exporter and not processor and headers:
            print(
                Fore.GREEN
                + f"Traceloop exporting traces to {api_endpoint}, authenticating with custom headers"
            )

        if api_key and not exporter and not processor and not headers:
            print(
                Fore.GREEN
                + f"Traceloop exporting traces to {api_endpoint} authenticating with bearer token"
            )
            headers = {
                "Authorization": f"Bearer {api_key}",
            }

        print(Fore.RESET)

        TracerWrapper.set_static_params(
            app_name, enable_content_tracing, api_endpoint, headers
        )
        Traceloop.__tracer_wrapper = TracerWrapper(
            disable_batch=disable_batch,
            processor=processor,
            propagator=propagator,
            exporter=exporter,
        )

    @staticmethod
    @deprecated(version="0.0.62", reason="Use set_association_properties instead")
    def set_correlation_id(correlation_id: str) -> None:
        set_correlation_id(correlation_id)

    def set_association_properties(properties: dict) -> None:
        set_association_properties(properties)

