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
from unittest.mock import MagicMock, patch

import streamlit as st
from streamlit.components.v2.component_registry import BidiComponentDefinition
from streamlit.proto.WidgetStates_pb2 import WidgetStates
from tests.delta_generator_test_case import DeltaGeneratorTestCase


def create_bidi_component_widget_states(
    widget_id: str, state_updates: dict, trigger_updates: dict
) -> WidgetStates:
    """Create a WidgetStates proto for a bidi component."""
    widget_state = WidgetStates()
    widget_state.widgets.add().id = widget_id
    widget_state.widgets[-1].json_value = json.dumps(
        {"state_updates": state_updates, "trigger_updates": trigger_updates}
    )
    return widget_state


def my_component(**kwargs):
    return st.bidi_component("my_component", **kwargs)


class BidiComponentsTest(DeltaGeneratorTestCase):
    def setUp(self):
        super().setUp()
        self.patch_registry = patch("streamlit.runtime.runtime.Runtime.instance")
        self.mock_runtime_instance = self.patch_registry.start()

        # Mock the component registry to return a valid definition
        self.mock_registry = MagicMock()
        self.mock_runtime_instance.return_value.bidi_component_registry = (
            self.mock_registry
        )

        def get_component_def(name):
            return BidiComponentDefinition(
                name,
                html=None,
                css=None,
                js="""
                export default function(props) {
                    // Mock JS content
                }
                """,
            )

        self.mock_registry.get.side_effect = get_component_def

    def tearDown(self):
        super().tearDown()
        self.patch_registry.stop()

    def test_initial_render(self):
        """Test that a bidi component renders correctly on its first run."""

        my_comp = my_component(key="my_comp")
        assert my_comp.get("value") is None

        c = self.get_delta_from_queue().new_element
        assert c.bidi_component.component_name == "my_component"

    def test_set_state_value(self):
        """Test that setStateValue updates the component's state and persists."""

        # Initial run
        my_comp = my_component(key="my_comp")
        assert my_comp.get("value") is None
        widget_id = self.get_delta_from_queue().new_element.bidi_component.id

        # Simulate a rerun with state update from the frontend
        widget_states = create_bidi_component_widget_states(
            widget_id, {"value": "bar"}, {}
        )
        self.script_run_ctx.session_state.on_script_will_rerun(widget_states)
        self.script_run_ctx.widget_user_keys_this_run.clear()
        self.script_run_ctx.widget_ids_this_run.clear()

        my_comp = my_component(key="my_comp")
        assert my_comp.get("value") == "bar"
        self.get_delta_from_queue()  # Clear the delta queue

        # Simulate another rerun with no new state from frontend
        self.script_run_ctx.session_state.on_script_will_rerun(WidgetStates())
        self.script_run_ctx.widget_user_keys_this_run.clear()
        self.script_run_ctx.widget_ids_this_run.clear()

        my_comp = my_component(key="my_comp")
        assert my_comp.get("value") == "bar"
