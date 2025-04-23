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
from typing import TYPE_CHECKING, Any, TypedDict, cast

from streamlit.elements.lib.event_utils import AttributeDictionary
from streamlit.elements.lib.form_utils import current_form_id
from streamlit.elements.lib.policies import check_cache_replay_rules
from streamlit.elements.lib.utils import compute_and_register_element_id, to_key

# Assuming protos are compiled and BidiComponentInstance is available:
from streamlit.proto.BidiComponent_pb2 import BidiComponent as BidiComponentProto
from streamlit.runtime.metrics_util import gather_metrics
from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx
from streamlit.runtime.state import register_widget

if TYPE_CHECKING:
    # Define DeltaGenerator for type checking the dg property
    from streamlit.delta_generator import DeltaGenerator
    from streamlit.runtime.state.common import WidgetCallback


INTERNAL_COMPONENT_NAME = "bidi_component"


class BidiComponentState(TypedDict, total=False):
    """
    The schema for the BidiComponent state.

    The state is stored in a dictionary-like object that supports both
    key and attribute notation. States cannot be programmatically changed
    or set through Session State.

    Attributes
    ----------
    value : Any
        The current value of the component instance returned from the frontend,
        or the default value if not yet set.
    """

    value: Any


@dataclass
class BidiComponentSerde:
    """Serialization/deserialization logic for BidiComponent.

    Assumes communication via JSON strings.
    """

    def deserialize(
        self,
        ui_value: str | None,
        widget_id: str = "",
    ) -> BidiComponentState:
        """Deserialize the state from the frontend.

        Args:
            ui_value: The JSON string received from the frontend.
            widget_id: The widget ID (unused here).

        Returns
        -------
            The deserialized state wrapped in an AttributeDictionary.
        """
        deserialized_value = json.loads(ui_value) if ui_value is not None else None
        state: BidiComponentState = {"value": deserialized_value}
        return cast("BidiComponentState", AttributeDictionary(state))

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


class BidiComponentMixin:
    """Mixin class for the bidi_component DeltaGenerator method."""

    @gather_metrics("bidi_component")
    def bidi_component(
        self,
        *,  # Make following args keyword-only
        js: str,
        key: str | None = None,
        default: Any = None,
        on_change: WidgetCallback | None = None,
    ) -> BidiComponentState:
        """Add a bidirectional component instance to the app.

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
        BidiComponentState
            A dictionary-like object representing the component's state,
            supporting attribute and key-based access for the 'value' field.
        """
        check_cache_replay_rules()

        key = to_key(key)

        # TODO: Add validation for the 'js' string? (e.g., basic syntax check?)

        ctx = get_script_run_ctx()

        # --- Widget Registration ---
        # The component's identity is determined by its name, form, the provided key,
        # AND the JS content itself. Changing the JS content will result in a new
        # widget ID and reset its state.
        computed_id = compute_and_register_element_id(
            INTERNAL_COMPONENT_NAME,
            user_key=key,
            form_id=current_form_id(self.dg),
            js_content=js,  # Always include js content in the ID hash
            # Add other relevant args here if they affect identity and should cause a reset
        )

        bidi_component_proto = BidiComponentProto()
        bidi_component_proto.component_name = INTERNAL_COMPONENT_NAME
        bidi_component_proto.js_content = js
        bidi_component_proto.form_id = current_form_id(self.dg)
        bidi_component_proto.id = computed_id

        # Instantiate the Serde for this component instance
        serde = BidiComponentSerde()

        component_state = register_widget(
            bidi_component_proto.id,
            # Pass the methods from the Serde object
            deserializer=serde.deserialize,
            serializer=serde.serialize,
            ctx=ctx,
            on_change_handler=on_change,
            # Keep value_type as before, register_widget requires it
            value_type="json_value",
        )

        # Enqueue using the dg instance and return the result of enqueue (a DeltaGenerator)
        # The actual widget value is handled by the state management
        self.dg._enqueue(INTERNAL_COMPONENT_NAME, bidi_component_proto)

        return cast("BidiComponentState", component_state.value)

    @property
    def dg(self) -> DeltaGenerator:
        """Get our DeltaGenerator."""
        return cast("DeltaGenerator", self)
