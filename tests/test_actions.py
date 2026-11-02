"""The Python helpers must produce the JS calls the bridge understands."""

import pytest
import reflex_vercel_analytics as rva
from reflex.event import EventSpec


def _script(spec: EventSpec) -> str:
    """The JavaScript string inside an rx.call_script event."""
    var = spec.args[0][1]
    return getattr(var, "_var_value", None) or str(var)


def test_track_builds_a_call_to_the_browser_api():
    spec = rva.track("Signup", {"method": "email"}, plan="pro")
    assert isinstance(spec, EventSpec)
    script = _script(spec)
    assert "window.__reflexVA" in script
    assert 'va.track("Signup", {"method": "email", "plan": "pro"}, null)' in script


def test_track_with_flags():
    script = _script(rva.track("Checkout", flags=["new-checkout"]))
    assert 'va.track("Checkout", {}, ["new-checkout"])' in script


def test_track_drops_none_values():
    script = _script(rva.track("Play", {"title": "intro", "duration": None}))
    assert '{"title": "intro"}' in script


@pytest.mark.parametrize("name", ["", "   ", "x" * 256, None, 42])
def test_invalid_event_names(name):
    with pytest.raises(ValueError):
        rva.validate_event_name(name)


def test_validate_properties_rejects_nested_values_and_long_strings():
    with pytest.raises(ValueError, match="nested"):
        rva.validate_properties({"items": [1, 2]})
    with pytest.raises(ValueError, match="nested"):
        rva.validate_properties({"meta": {"a": 1}})
    with pytest.raises(ValueError, match="longer"):
        rva.validate_properties({"long": "x" * 256})
    with pytest.raises(ValueError, match="longer"):
        rva.validate_properties({"k" * 256: "v"})
    with pytest.raises(ValueError, match="keys"):
        rva.validate_properties({"": "v"})


def test_validate_properties_keeps_scalars():
    assert rva.validate_properties({"a": 1, "b": 2.5, "c": True, "d": "x", "e": None}) == {
        "a": 1,
        "b": 2.5,
        "c": True,
        "d": "x",
    }


def test_page_view_defaults():
    assert "va.pageView(null, null)" in _script(rva.page_view())
    assert 'va.pageView("/wizard/step-2", "/wizard/[step]")' in _script(
        rva.page_view("/wizard/step-2", route="/wizard/[step]")
    )


def test_opt_out_and_opt_in():
    assert "va.optOut()" in _script(rva.opt_out())
    assert "va.optIn()" in _script(rva.opt_in())


def test_get_status_takes_a_callback():
    import reflex as rx

    class S(rx.State):
        @rx.event
        def receive(self, status: dict):
            pass

    spec = rva.get_status(S.receive)
    assert "va.status()" in _script(spec)
    assert len(spec.args) == 2  # script + callback
