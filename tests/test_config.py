"""Config loading, validation, environment overrides and prop rendering."""

import json

import pytest
import reflex_vercel_analytics as rva


def test_defaults_are_inert_but_valid():
    config = rva.VercelAnalyticsConfig()
    assert config.enabled is True
    assert config.mode == "auto"
    assert config.debug is None
    assert config.exclude_paths == []
    assert config.to_props(prod=False) == {
        "enabled": True,
        "mode": "development",
        "track_page_views": True,
        "include_search": True,
        "respect_do_not_track": False,
    }


def test_auto_mode_resolves_from_the_reflex_run_mode():
    config = rva.VercelAnalyticsConfig()
    assert config.effective_mode(prod=True) == "production"
    assert config.effective_mode(prod=False) == "development"
    assert rva.VercelAnalyticsConfig(mode="production").effective_mode(prod=False) == "production"


def test_invalid_values_raise_config_error():
    with pytest.raises(rva.ConfigError):
        rva.VercelAnalyticsConfig(mode="staging")
    with pytest.raises(rva.ConfigError):
        rva.VercelAnalyticsConfig(exclude_paths=["admin"])
    with pytest.raises(rva.ConfigError):
        rva.VercelAnalyticsConfig(client_config="not json")
    with pytest.raises(rva.ConfigError):
        rva.VercelAnalyticsConfig(client_config="[1, 2]")


def test_unknown_keys_are_rejected():
    with pytest.raises(rva.ConfigError, match="unknown keys"):
        rva.VercelAnalyticsConfig.from_mapping({"measurement_id": "G-1"})


def test_toml_file_top_level_and_table(tmp_path):
    top = tmp_path / "vercel_analytics.toml"
    top.write_text('mode = "production"\nexclude_paths = ["/admin/*"]\n', encoding="utf-8")
    config = rva.VercelAnalyticsConfig.from_file(top)
    assert config.mode == "production"
    assert config.exclude_paths == ["/admin/*"]
    assert config.source == str(top)

    table = tmp_path / "shared.toml"
    table.write_text("[vercel_analytics]\ndebug = false\n", encoding="utf-8")
    assert rva.VercelAnalyticsConfig.from_file(table).debug is False


def test_pyproject_table_and_json(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.reflex-vercel-analytics]\ninclude_search = false\n", encoding="utf-8")
    assert rva.VercelAnalyticsConfig.from_file(pyproject).include_search is False

    as_json = tmp_path / "va.json"
    as_json.write_text(json.dumps({"dsn": "abc123", "redact_search_params": ["token"]}), encoding="utf-8")
    config = rva.VercelAnalyticsConfig.from_file(as_json)
    assert config.dsn == "abc123"
    assert config.redact_search_params == ["token"]


def test_missing_file(tmp_path):
    with pytest.raises(rva.ConfigError, match="not found"):
        rva.VercelAnalyticsConfig.from_file(tmp_path / "nope.toml")


def test_find_config_file_order(tmp_path, monkeypatch):
    monkeypatch.delenv("VERCEL_ANALYTICS_CONFIG", raising=False)
    assert rva.find_config_file(tmp_path) is None

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'x'\n", encoding="utf-8")
    assert rva.find_config_file(tmp_path) is None
    pyproject.write_text("[tool.reflex-vercel-analytics]\nmode = 'production'\n", encoding="utf-8")
    assert rva.find_config_file(tmp_path) == pyproject

    toml = tmp_path / rva.DEFAULT_CONFIG_FILENAME
    toml.write_text("", encoding="utf-8")
    assert rva.find_config_file(tmp_path) == toml

    monkeypatch.setenv("VERCEL_ANALYTICS_CONFIG", "/elsewhere/va.toml")
    assert str(rva.find_config_file(tmp_path)) == "/elsewhere/va.toml"


def test_env_overrides():
    config = rva.VercelAnalyticsConfig(mode="production").with_env(
        {
            "VERCEL_ANALYTICS_MODE": "development",
            "VERCEL_ANALYTICS_DEBUG": "false",
            "VERCEL_ANALYTICS_ENABLED": "0",
            "VERCEL_ANALYTICS_EXCLUDE_PATHS": "/admin/*, /preview",
            "VERCEL_ANALYTICS_SCRIPT_SRC": "https://cdn.example.com/script.js",
        }
    )
    assert config.mode == "development"
    assert config.debug is False
    assert config.enabled is False
    assert config.exclude_paths == ["/admin/*", "/preview"]
    assert config.script_src == "https://cdn.example.com/script.js"
    assert config.source == "defaults + env"


def test_env_bool_must_be_boolean():
    with pytest.raises(rva.ConfigError, match="VERCEL_ANALYTICS_ENABLED"):
        rva.VercelAnalyticsConfig().with_env({"VERCEL_ANALYTICS_ENABLED": "maybe"})


def test_vercel_build_variables_fill_client_config_and_base_path():
    client = json.dumps({"analytics": {"scriptSrc": "/_vercel/x/script.js"}})
    config = rva.VercelAnalyticsConfig().with_env(
        {"VERCEL_OBSERVABILITY_CLIENT_CONFIG": client, "VERCEL_OBSERVABILITY_BASEPATH": "/_vercel"}
    )
    assert config.client_config == client
    assert config.base_path == "/_vercel"
    # Explicit values win over Vercel's.
    explicit = rva.VercelAnalyticsConfig(base_path="/mine").with_env(
        {"VERCEL_OBSERVABILITY_BASEPATH": "/_vercel"}
    )
    assert explicit.base_path == "/mine"
    assert explicit.source is None  # nothing changed, same object


def test_no_env_changes_returns_same_object():
    config = rva.VercelAnalyticsConfig()
    assert config.with_env({}) is config


def test_to_props_includes_optional_fields():
    config = rva.VercelAnalyticsConfig(
        mode="production",
        debug=False,
        dsn="dsn1",
        event_endpoint="/x/event",
        base_path="/_vercel",
        client_config='{"analytics": {}}',
        exclude_paths=["/admin/*"],
        redact_search_params=["token"],
        include_search=False,
    )
    props = config.to_props()
    assert props["mode"] == "production"
    assert props["debug"] is False
    assert props["dsn"] == "dsn1"
    assert props["event_endpoint"] == "/x/event"
    assert props["base_path"] == "/_vercel"
    assert props["config_string"] == '{"analytics": {}}'
    assert props["exclude_paths"] == ["/admin/*"]
    assert props["redact_search_params"] == ["token"]
    assert props["include_search"] is False
    assert "script_src" not in props


def test_load_config(tmp_path, monkeypatch):
    monkeypatch.delenv("VERCEL_ANALYTICS_CONFIG", raising=False)
    path = tmp_path / "va.toml"
    path.write_text('mode = "production"\n', encoding="utf-8")
    config = rva.load_config(path, environ={"VERCEL_ANALYTICS_DEBUG": "true"})
    assert config.mode == "production"
    assert config.debug is True
    assert rva.load_config(path, env=False).debug is None
