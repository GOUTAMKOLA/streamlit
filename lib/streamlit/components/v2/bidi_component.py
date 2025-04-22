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

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from streamlit.delta_generator_singletons import get_dg_singleton_instance
from streamlit.elements.lib.form_utils import current_form_id
from streamlit.elements.lib.policies import check_cache_replay_rules
from streamlit.elements.lib.utils import compute_and_register_element_id

# Assuming protos are compiled and BidiComponentInstance is available:
from streamlit.proto.BidiComponent_pb2 import BidiComponent as BidiComponentProto
from streamlit.proto.Element_pb2 import Element
from streamlit.runtime.metrics_util import gather_metrics
from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx
from streamlit.runtime.state import register_widget

if TYPE_CHECKING:
    from streamlit.runtime.state.common import RegisterWidgetResult, WidgetCallback


@dataclass
class BidiComponentSerde:
    """Serialization/deserialization logic for BidiComponent.

    Assumes communication via JSON strings.
    """

    default: Any

    def deserialize(
        self,
        ui_value: str | None,
        widget_id: str = "",
    ) -> Any:
        """Deserialize the value from the frontend.

        Args:
            ui_value: The JSON string received from the frontend.
            widget_id: The widget ID (unused here).

        Returns
        -------
            The deserialized value, or the default if ui_value is None.
        """
        return json.loads(ui_value) if ui_value is not None else self.default

    def serialize(self, value: Any) -> str:
        """Serialize the value to be sent to the frontend.

        Args:
            value: The value to serialize.

        Returns
        -------
            A JSON string representation of the value.
        """
        # Frontend might expect a specific format; adjust as needed.
        # Defaulting to JSON serialization.
        return json.dumps(value)


class BidiComponent:
    def __init__(self, component_name: str):
        self.component_name = component_name

    @gather_metrics("bidi_component")
    def __call__(
        self,
        *,  # Make following args keyword-only
        js: str,
        key: str | None = None,
        default: Any = None,
        on_change: WidgetCallback | None = None,
        # **kwargs: Any, # Add later if needed for other args
    ) -> Any:
        """Create a new instance of the bidirectional component.

        Parameters
        ----------
        js : str
            The JavaScript code string for the component.
        key : str or None
            An optional string to use as the unique key for the component.
            If this is omitted, a key will be generated based on the
            component's execution sequence.
        default: any or None
            The default return value for the component. This is returned when
            the component's frontend hasn't yet specified a value.
        on_change: WidgetCallback or None
            An optional callback invoked when the component's value changes.

        Returns
        -------
        any or None
            The component's current value.

        """
        check_cache_replay_rules()

        # TODO: Add validation for the 'js' string? (e.g., basic syntax check?)

        ctx = get_script_run_ctx()
        element = Element()
        dg = get_dg_singleton_instance().main_dg  # Use main DG for now

        component_instance_proto = BidiComponentProto()
        component_instance_proto.component_name = self.component_name
        component_instance_proto.js_content = js
        component_instance_proto.form_id = current_form_id(dg)

        # --- Widget Registration ---
        # The component's identity is determined by its name, form, the provided key,
        # AND the JS content itself. Changing the JS content will result in a new
        # widget ID and reset its state.
        computed_id = compute_and_register_element_id(
            "bidi_component_instance",
            user_key=key,
            form_id=component_instance_proto.form_id,
            component_name=self.component_name,
            js_content=js,  # Always include js content in the ID hash
            # Add other relevant args here if they affect identity and should cause a reset
        )

        component_instance_proto.id = computed_id

        # Instantiate the Serde for this component instance
        serde = BidiComponentSerde(default=default)

        component_state: RegisterWidgetResult[Any] = register_widget(
            element_id=component_instance_proto.id,
            # Pass the methods from the Serde object
            deserializer=serde.deserialize,
            serializer=serde.serialize,
            ctx=ctx,
            on_change_handler=on_change,
            # Keep value_type as before, register_widget requires it
            value_type="json_value",
        )

        # The deserializer now handles the default value case
        widget_value = component_state.value

        # Assign the populated proto to the Element message
        element.bidi_component.CopyFrom(component_instance_proto)

        dg._enqueue("bidi_component_instance", element.bidi_component)
        return widget_value
