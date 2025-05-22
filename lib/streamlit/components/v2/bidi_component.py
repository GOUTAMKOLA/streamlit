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
from streamlit.errors import StreamlitAPIException

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

    def deserialize(self, ui_value: str | dict | None) -> BidiComponentState:
        """Deserialize the state from the frontend.

        Args:
            ui_value: The JSON string received from the frontend.

        Returns
        -------
            The deserialized state wrapped in an AttributeDictionary.
        """
        try:
            if isinstance(ui_value, dict):
                deserialized_value = ui_value
            elif ui_value is not None:
                if isinstance(ui_value, (int, float, bool)):
                    deserialized_value = ui_value
                else:
                    deserialized_value = json.loads(ui_value)
            else:
                deserialized_value = None
        except Exception:
            # TODO: Should we raise an error here? Should we let the user know?
            deserialized_value = None

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
        component_name: str,
        *args: Any,
        key: str | None = None,
        default: Any = None,
        on_change: WidgetCallback | None = None,
        child_container_count: int = 0,
        # TODO: This needs to have a better type + support Arrow
        data: Any | None = None,
        **kwargs: Any,
    ) -> BidiComponentState:
        """Add a bidirectional component instance to the app using a registered component.

        Parameters
        ----------
        component_name : str
            The name of the registered component to use. The component's HTML, CSS,
            and JS will be loaded from the registry.
        *args
            Positional arguments to pass to the component.
        key : str or None
            An optional string to use as the unique key for the component.
            If this is omitted, a key will be generated based on the
            component's execution sequence.
        default: any or None
            The default return value for the component. This is returned when
            the component's frontend hasn't yet specified a value.
        on_change: WidgetCallback or None
            An optional callback invoked when the component's value changes.
        child_container_count : int
            The number of child containers this component has. Default is 0.
        **kwargs
            Keyword arguments to pass to the component.

        Returns
        -------
        BidiComponentState
            A dictionary-like object representing the component's state,
            supporting attribute and key-based access for the 'value' field.

        Raises
        ------
        ValueError
            If the component is not registered in the registry.
        StreamlitAPIException
            If the component does not have the required JavaScript or HTML content.
        """
        check_cache_replay_rules()

        key = to_key(key)
        ctx = get_script_run_ctx()

        if ctx is None:
            # Create an empty state with the default value and return it
            state: BidiComponentState = {"value": default}
            return cast("BidiComponentState", AttributeDictionary(state))

        # Get the component definition from the registry
        from streamlit.runtime import Runtime

        registry = Runtime.instance().bidi_component_registry
        component_def = registry.get(component_name)

        if component_def is None:
            raise ValueError(f"Component '{component_name}' is not registered")

        # Validate that the component has the required content
        has_js = bool(component_def.js_content or component_def.js_url)
        has_html = bool(component_def.html_content)

        if not has_js and not has_html:
            raise StreamlitAPIException(
                f"Component '{component_name}' must have either JavaScript content "
                "(js_content or js_url) or HTML content (html_content), or both. "
                "Please ensure the component definition includes at least one of these."
            )

        # Compute a unique ID for this component instance
        computed_id = compute_and_register_element_id(
            component_name,
            user_key=key,
            form_id=current_form_id(self.dg),
        )

        handlers: dict[str, WidgetCallback] = {}
        if callable(on_change):
            handlers["change"] = on_change

        # Example for other handlers like on_click from kwargs
        # We can make this more robust or configurable if needed.
        for kwarg_key, kwarg_value in kwargs.items():
            if kwarg_key.startswith("on_") and callable(kwarg_value):
                event_name = kwarg_key[3:]  # remove "on_"
                if event_name:  # Ensure we have an event name
                    handlers[event_name] = kwarg_value

        # Set up the component proto
        bidi_component_proto = BidiComponentProto()
        bidi_component_proto.id = computed_id
        bidi_component_proto.component_name = component_name
        bidi_component_proto.js_content = component_def.js_content or ""
        bidi_component_proto.js_source_path = component_def.js_url or ""
        bidi_component_proto.html_content = component_def.html_content or ""
        bidi_component_proto.css_content = component_def.css_content or ""
        bidi_component_proto.css_source_path = component_def.css_url or ""
        bidi_component_proto.isolate_styles = component_def.isolate_styles
        # TODO: Support dataframes via Arrow
        bidi_component_proto.data = json.dumps(data) if data else ""
        bidi_component_proto.child_container_count = child_container_count
        bidi_component_proto.form_id = current_form_id(self.dg)
        if handlers:
            bidi_component_proto.registered_handler_names.extend(handlers.keys())

        # Instantiate the Serde for this component instance
        serde = BidiComponentSerde()

        component_state = register_widget(
            bidi_component_proto.id,
            deserializer=serde.deserialize,
            serializer=serde.serialize,
            ctx=ctx,
            callbacks=handlers if handlers else None,
            value_type="json_value",
        )

        # Enqueue using the dg instance
        self.dg._enqueue(INTERNAL_COMPONENT_NAME, bidi_component_proto)

        return cast("BidiComponentState", component_state.value)

    @property
    def dg(self) -> DeltaGenerator:
        """Get our DeltaGenerator."""
        return cast("DeltaGenerator", self)
