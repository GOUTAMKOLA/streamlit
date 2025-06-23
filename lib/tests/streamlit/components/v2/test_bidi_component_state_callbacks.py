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

import json
import unittest
from unittest.mock import MagicMock, patch

import streamlit as st
from streamlit.components.v2.component_registry import (
    BidiComponentDefinition,
    BidiComponentRegistry,
)
from streamlit.proto.WidgetStates_pb2 import WidgetState, WidgetStates
from streamlit.runtime import Runtime
from tests.delta_generator_test_case import DeltaGeneratorTestCase


class BidiComponentStateCallbackTest(DeltaGeneratorTestCase):
    """Verify that per-state callbacks fire exclusively for their key."""

    COMPONENT_NAME = "stateful_component"

    def setUp(self):
        super().setUp()
        # Set up a fresh registry patched into the Runtime singleton.
        self.mock_registry = BidiComponentRegistry()
        self.runtime_patcher = patch.object(
            Runtime, "instance", return_value=MagicMock()
        )
        self.mock_runtime = self.runtime_patcher.start()
        self.mock_runtime.return_value.bidi_component_registry = self.mock_registry

        # Register a minimal component definition (JS only is enough for backend tests).
        self.mock_registry.register(
            BidiComponentDefinition(name=self.COMPONENT_NAME, js="console.log('hi');")
        )

        # Prepare per-event callback mocks.
        self.range_cb = MagicMock(name="range_cb")
        self.text_cb = MagicMock(name="text_cb")

        # First script run: render the component and capture its widget id.
        st.bidi_component(
            self.COMPONENT_NAME,
            on_range_change=self.range_cb,
            on_text_change=self.text_cb,
        )
        self.component_id = (
            self.get_delta_from_queue().new_element.bidi_component.id  # type: ignore[attr-defined]
        )
        # Sanity: no callbacks should have fired during initial render.
        self.range_cb.assert_not_called()
        self.text_cb.assert_not_called()

    def tearDown(self):
        super().tearDown()
        self.runtime_patcher.stop()

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------
    def _simulate_state_update(self, new_state: dict):
        """Trigger a faux frontend state update and run callbacks."""
        ws = WidgetState(id=self.component_id)
        ws.json_value = json.dumps(new_state)
        self.script_run_ctx.session_state.on_script_will_rerun(
            WidgetStates(widgets=[ws])
        )

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_only_range_changes_invokes_only_range_callback(self):
        # Update just the "range" key.
        self._simulate_state_update({"range": 10})

        self.range_cb.assert_called_once()
        self.text_cb.assert_not_called()

    def test_only_text_changes_invokes_only_text_callback(self):
        # Reset mock call history.
        self.range_cb.reset_mock()
        self.text_cb.reset_mock()

        # Update just the "text" key.
        self._simulate_state_update({"text": "hello"})

        self.text_cb.assert_called_once()
        self.range_cb.assert_not_called()

    def test_both_keys_change_invokes_both_callbacks(self):
        # Reset mock call history.
        self.range_cb.reset_mock()
        self.text_cb.reset_mock()

        # Update both keys simultaneously.
        self._simulate_state_update({"range": 77, "text": "world"})

        self.range_cb.assert_called_once()
        self.text_cb.assert_called_once()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
