# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022-2025)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for *trigger* behaviour in ``st.bidi_component``.

The tests below focus on verifying that *per-event* trigger callbacks are
executed **exclusively** for the event whose value changed. They mirror the
behavioural guarantees laid out in section *6 Multi-callback semantics* of the
product plan documented in ``llm_docs/bidi_components_plan.md``.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import streamlit as st
from streamlit.components.v2.bidi_component import make_trigger_id
from streamlit.components.v2.component_registry import (
    BidiComponentDefinition,
    BidiComponentRegistry,
)
from streamlit.proto.WidgetStates_pb2 import WidgetState, WidgetStates
from streamlit.runtime import Runtime
from tests.delta_generator_test_case import DeltaGeneratorTestCase


class BidiComponentTriggerCallbackTest(DeltaGeneratorTestCase):
    """Verify that per-event *trigger* callbacks fire only for their event."""

    COMPONENT_NAME = "trigger_component"

    # ------------------------------------------------------------------
    # Test lifecycle helpers
    # ------------------------------------------------------------------
    def setUp(self):
        super().setUp()

        # Patch a fresh registry into the Runtime singleton so tests are isolated.
        self.registry = BidiComponentRegistry()
        self.runtime_patcher = patch.object(
            Runtime, "instance", return_value=MagicMock()
        )
        self.mock_runtime = self.runtime_patcher.start()
        self.mock_runtime.return_value.bidi_component_registry = self.registry

        # Register a minimal JS-only component definition (enough for backend tests).
        self.registry.register(
            BidiComponentDefinition(name=self.COMPONENT_NAME, js="console.log('hi');")
        )

        # Prepare mocks for per-event callbacks.
        self.range_trigger_cb = MagicMock(name="range_trigger_cb")
        self.text_trigger_cb = MagicMock(name="text_trigger_cb")
        self.button_cb = MagicMock(name="button_cb")

        # First script run: render the component and capture its widget id.
        st.bidi_component(
            self.COMPONENT_NAME,
            on_range_change=self.range_trigger_cb,
            on_text_change=self.text_trigger_cb,
        )

        # Render a separate *button* widget that uses the classic trigger_value
        # mechanism so we can verify coexistence of multiple trigger sources.
        st.button("Click me!", on_click=self.button_cb)

        # After enqueuing both the component and the button, the button proto
        # is at the tail of the queue (index -1) and the component proto just
        # before that (index -2).

        self.button_id = self.get_delta_from_queue().new_element.button.id  # type: ignore[attr-defined]

        self.component_id = (
            self.get_delta_from_queue(-2).new_element.bidi_component.id  # type: ignore[attr-defined]
        )

        # Sanity: no callbacks should have fired during initial render.
        self.range_trigger_cb.assert_not_called()
        self.text_trigger_cb.assert_not_called()
        self.button_cb.assert_not_called()

    def tearDown(self):
        super().tearDown()
        # Stop Runtime.instance patcher started in setUp.
        self.runtime_patcher.stop()

    # ------------------------------------------------------------------
    # Utility to simulate frontend trigger updates
    # ------------------------------------------------------------------
    def _simulate_trigger_update(self, trigger_updates: dict[str, Any]):
        """Emulate the frontend firing one or more triggers.

        Parameters
        ----------
        trigger_updates : Dict[str, Any]
            Mapping from *event name* to *payload* value. The payload will be
            JSON-serialised before being injected into the ``WidgetState``
            protobuf.
        """

        widget_states = WidgetStates()
        for event_name, payload in trigger_updates.items():
            ws = WidgetState(id=make_trigger_id(self.component_id, event_name))
            ws.json_trigger_value = json.dumps(payload)
            widget_states.widgets.append(ws)

        # Feed the simulated WidgetStates into Session State which will, in
        # turn, invoke the appropriate callbacks via ``_call_callbacks``.
        self.script_run_ctx.session_state.on_script_will_rerun(widget_states)

    def _simulate_button_click(self):
        """Simulate a user clicking the separate st.button widget."""

        ws = WidgetState(id=self.button_id)
        ws.trigger_value = True
        widget_states = WidgetStates(widgets=[ws])
        self.script_run_ctx.session_state.on_script_will_rerun(widget_states)

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_only_range_trigger_invokes_only_range_callback(self):
        """Updating only the ``range`` trigger should only call its callback."""

        self._simulate_trigger_update({"range": 10})

        self.range_trigger_cb.assert_called_once()
        self.text_trigger_cb.assert_not_called()

        # Value assertions
        range_id = make_trigger_id(self.component_id, "range")
        assert self.script_run_ctx.session_state[range_id] == 10

    def test_only_text_trigger_invokes_only_text_callback(self):
        """Updating only the ``text`` trigger should only call its callback."""

        self._simulate_trigger_update({"text": "hello"})

        self.text_trigger_cb.assert_called_once()
        self.range_trigger_cb.assert_not_called()

    def test_both_triggers_fired_invokes_both_callbacks(self):
        """When *both* triggers fire simultaneously, *both* callbacks fire."""

        self._simulate_trigger_update({"range": 77, "text": "world"})

        self.range_trigger_cb.assert_called_once()
        self.text_trigger_cb.assert_called_once()

    # --------------------------------------------------------------
    # Interactions involving *another* trigger widget (st.button)
    # --------------------------------------------------------------

    def test_button_click_invokes_only_button_callback(self):
        """Clicking the separate st.button must not affect component triggers."""

        self._simulate_button_click()

        self.button_cb.assert_called_once()
        self.range_trigger_cb.assert_not_called()
        self.text_trigger_cb.assert_not_called()

        # After a button click, the *previous* range trigger should have been
        # reset to ``None`` by SessionState._reset_triggers.
        range_id = make_trigger_id(self.component_id, "range")
        assert self.script_run_ctx.session_state[range_id] is None

        self._simulate_trigger_update({"range": 10})

        self.button_cb.assert_called_once()
        self.range_trigger_cb.assert_called_once()
        self.text_trigger_cb.assert_not_called()

    def test_button_and_component_trigger_both_fire(self):
        """Simultaneous component trigger + button click fires *all* callbacks."""

        # Compose a single WidgetStates message that includes both updates.
        widget_states = WidgetStates()

        # Component trigger for 'range'
        ws_component = WidgetState(id=make_trigger_id(self.component_id, "range"))
        ws_component.json_trigger_value = json.dumps(123)
        widget_states.widgets.append(ws_component)

        # Button click
        ws_button = WidgetState(id=self.button_id)
        ws_button.trigger_value = True
        widget_states.widgets.append(ws_button)

        # Act
        self.script_run_ctx.session_state.on_script_will_rerun(widget_states)

        # Assert: all three callbacks should have fired accordingly.
        self.range_trigger_cb.assert_called_once()
        self.button_cb.assert_called_once()
        # text trigger remains untouched
        self.text_trigger_cb.assert_not_called()


if __name__ == "__main__":  # pragma: no cover
    import pytest

    pytest.main([__file__])
