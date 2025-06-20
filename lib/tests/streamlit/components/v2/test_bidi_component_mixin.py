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

"""Unit tests for the enhanced ``st.bidi_component`` implementation.

Focus areas:
1. Parsing of ``on_<event>_change`` kwargs into event-callback mapping.
2. Verification that per-event *trigger widgets* are registered with
   ``json_trigger_value`` as their value_type.
3. The returned :class:`BidiComponentResult` merges persistent state and
   trigger values.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import streamlit as st
from streamlit.components.v2.bidi_component import (
    EVENT_DELIM,
    BidiComponentResult,
    make_trigger_id,
)
from streamlit.components.v2.component_registry import (
    BidiComponentDefinition,
    BidiComponentRegistry,
)
from streamlit.runtime import Runtime
from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx
from tests.delta_generator_test_case import DeltaGeneratorTestCase


class BidiComponentMixinTest(DeltaGeneratorTestCase):
    """Tests for the richer BidiComponent behaviour (stage 3.2)."""

    def setUp(self):
        super().setUp()
        # Create and inject a fresh registry for each test run
        self.registry = BidiComponentRegistry()
        runtime = Runtime.instance()
        if runtime is None:
            raise RuntimeError("Runtime.instance() returned None in test setup.")
        runtime.bidi_component_registry = self.registry

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    def _register_dummy_component(self, name: str = "dummy") -> None:
        self.registry.register(
            BidiComponentDefinition(name=name, js="console.log('hi');")
        )

    # ---------------------------------------------------------------------
    # Tests
    # ---------------------------------------------------------------------
    def test_event_callback_parsing_and_trigger_widget_registration(self):
        """Providing ``on_click_change`` should register a trigger widget."""

        self._register_dummy_component()

        on_click_cb = MagicMock(name="on_click_cb")
        on_hover_cb = MagicMock(name="on_hover_cb")

        # Act
        result = st.bidi_component(
            "dummy",
            on_click_change=on_click_cb,
            on_hover_change=on_hover_cb,
        )

        # ------------------------------------------------------------------
        # Assert - return type & merged keys
        # ------------------------------------------------------------------
        assert isinstance(result, BidiComponentResult)
        # No state set yet, but we expect trigger keys to exist with None
        assert "click" in result
        assert result.click is None
        assert "hover" in result
        assert result.hover is None

        # ------------------------------------------------------------------
        # Assert - trigger widget metadata
        # ------------------------------------------------------------------
        ctx = get_script_run_ctx()
        assert ctx is not None, "ScriptRunContext missing in test"

        # Compute expected trigger ids
        base_id = next(
            wid
            for wid in ctx.session_state
            if wid.startswith("$$ID") and EVENT_DELIM not in wid
        )
        expected_click_id = make_trigger_id(base_id, "click")
        expected_hover_id = make_trigger_id(base_id, "hover")

        metadata_click = ctx.session_state._new_widget_state.widget_metadata[
            expected_click_id
        ]
        metadata_hover = ctx.session_state._new_widget_state.widget_metadata[
            expected_hover_id
        ]

        assert metadata_click.value_type == "json_trigger_value"
        assert metadata_hover.value_type == "json_trigger_value"

        # The callbacks must be wired to the "change" event in metadata
        assert metadata_click.callbacks == {"change": on_click_cb}
        assert metadata_hover.callbacks == {"change": on_hover_cb}


if __name__ == "__main__":
    pytest.main([__file__])
