"""The component must compile to the JSX the bridge understands."""

from types import SimpleNamespace

import reflex as rx
import reflex_vercel_analytics as rva


class DemoState(rx.State):
    @rx.event
    def on_page_view(self, payload: dict):
        pass


def test_library_points_to_the_shared_jsx_bridge():
    assert rva.VercelAnalytics.library.startswith("$/public/external/reflex_vercel_analytics/")
    assert rva.VercelAnalytics.library.endswith("vercel_analytics.jsx")
    assert rva.VercelAnalytics.tag == "ReflexVercelAnalytics"


def test_vercel_analytics_is_pinned():
    assert rva.VERCEL_ANALYTICS_VERSION == "2.0.1"
    component = rva.vercel_analytics(config=False)
    assert component.lib_dependencies == ["@vercel/analytics@2.0.1"]


def test_props_compile_to_camel_case():
    rendered = str(
        rva.vercel_analytics(
            config=False,
            mode="production",
            debug=False,
            track_page_views=False,
            include_search=False,
            exclude_paths=["/admin/*"],
            redact_search_params=["token"],
            script_src="https://cdn.example.com/script.js",
            event_endpoint="/x/event",
            config_string='{"analytics": {}}',
        )
    )
    for expected in (
        'mode:"production"',
        "debug:false",
        "trackPageViews:false",
        "includeSearch:false",
        "excludePaths:",
        "redactSearchParams:",
        'scriptSrc:"https://cdn.example.com/script.js"',
        'eventEndpoint:"/x/event"',
        "configString:",
    ):
        assert expected in rendered


def test_config_object_and_explicit_props_merge():
    config = rva.VercelAnalyticsConfig(mode="production", debug=True)
    rendered = str(rva.vercel_analytics(config=config, debug=False))
    assert 'mode:"production"' in rendered
    assert "debug:false" in rendered  # explicit prop wins


def test_config_path(tmp_path):
    path = tmp_path / "va.toml"
    path.write_text('mode = "production"\ndsn = "dsn-from-file"\n', encoding="utf-8")
    assert 'dsn:"dsn-from-file"' in str(rva.vercel_analytics(config=str(path)))


def test_event_triggers():
    component = rva.vercel_analytics(config=False, on_page_view=DemoState.on_page_view)
    assert "on_page_view" in component.event_triggers
    assert {"on_ready", "on_page_view", "on_event"} <= set(component.get_event_triggers())


def test_install_adds_an_app_wrap():
    app = rx.App()
    rva.install(app, config=rva.VercelAnalyticsConfig(mode="production"), on_page_view=DemoState.on_page_view)
    wrap = app.extra_app_wraps[(1, "VercelAnalytics")]
    component = wrap(True)
    assert isinstance(component, rva.VercelAnalytics)
    assert 'mode:"production"' in str(component)


def test_install_custom_order_and_disabled_config():
    # install() only touches extra_app_wraps; a stub avoids a second rx.App per process.
    app = SimpleNamespace(extra_app_wraps={})
    rva.install(app, config=False, order=7, enabled=False)
    assert "enabled:false" in str(app.extra_app_wraps[(7, "VercelAnalytics")](True))
