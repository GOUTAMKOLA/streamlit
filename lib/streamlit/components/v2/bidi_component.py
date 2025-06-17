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

from streamlit.elements.lib.form_utils import current_form_id
from streamlit.elements.lib.policies import check_cache_replay_rules
from streamlit.elements.lib.utils import compute_and_register_element_id, to_key
from streamlit.errors import StreamlitAPIException

# Assuming protos are compiled and BidiComponentInstance is available:
from streamlit.proto.BidiComponent_pb2 import BidiComponent as BidiComponentProto
from streamlit.runtime.metrics_util import gather_metrics
from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx
from streamlit.runtime.state.widgets import register_widget
from streamlit.util import AttributeDictionary

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


class BidiComponentResult(AttributeDictionary):
    """
    Result object from st.components.v2.component containing both
    a DeltaGenerator and component state values.

    This class supports both .property and ["dictionary"] access patterns
    and handles state values (persistent) vs trigger values (reset to None on rerun).

    Attributes
    ----------
    delta_generator : DeltaGenerator
        The DeltaGenerator instance for this component
    **state_values : Any
        The merged state and trigger values as attributes/dictionary keys
    """

    def __init__(self, delta_generator: DeltaGenerator, state_values: dict[str, Any]):
        # Store delta_generator as a special property and merge with state values
        super().__init__({"delta_generator": delta_generator, **state_values})

    @property
    def delta_generator(self) -> DeltaGenerator:
        """Get the DeltaGenerator for this component."""
        return self["delta_generator"]


@dataclass
class BidiComponentSerde:
    """Serialization/deserialization logic for BidiComponent with state/trigger differentiation.

    This new implementation supports the dual-mode state management system:
    - State Values: Persistent across reruns until explicitly changed
    - Trigger Values: Reset to None at the start of each script run
    """

    def deserialize(self, ui_value: str | dict | None) -> BidiComponentState:
        """Deserialize the state sent from the frontend.

        The frontend is expected to send a JSON-serialisable mapping whose keys
        correspond to event names (including ordinary persistent values and
        trigger-style events). For legacy reasons a plain scalar may still be
        sent – in that case we wrap it in a one-item mapping with key
        ``"value"``.
        """
        try:
            if isinstance(ui_value, dict):
                data = ui_value
            elif ui_value is not None:
                # Scalars or JSON-encoded strings
                if isinstance(ui_value, (int, float, bool)):
                    data = {"value": ui_value}
                else:
                    data = json.loads(ui_value)
            else:
                data = {}
        except Exception:
            data = {}

        # Return the mapping directly – Streamlit core now handles event keys
        # generically, so there is no need for the nested "value" indirection
        # nor for the bespoke BidiComponentWidgetState container.
        return cast("BidiComponentState", AttributeDictionary(data))

    def serialize(self, value: Any) -> str:
        """Serialize *value* for transport to the frontend."""
        return json.dumps(value)


class BidiComponentMixin:
    """Mixin class for the bidi_component DeltaGenerator method."""

    @gather_metrics("bidi_component")
    def bidi_component(
        self,
        component_name: str,
        key: str | None = None,
        default: Any = None,
        child_container_count: int = 0,
        # TODO: This needs to have a better type + support Arrow
        data: Any | None = None,
        **on_callbacks: WidgetCallback,
    ) -> BidiComponentResult:
        """Add a bidirectional component instance to the app using a registered component.

        Parameters
        ----------
        component_name : str
            The name of the registered component to use. The component's HTML, CSS,
            and JS will be loaded from the registry.
        key : str or None
            An optional string to use as the unique key for the component.
            If this is omitted, a key will be generated based on the
            component's execution sequence.
        default: any or None
            The default return value for the component. This is returned when
            the component's frontend hasn't yet specified a value.
        child_container_count : int
            The number of child containers this component has. Default is 0.
        data : Any or None
            Data to pass to the component (JSON-serializable).
        **on_callbacks : WidgetCallback
            Callback functions for handling component events. Use pattern
            on_{state_name}_change (e.g., on_click_change, on_value_change).

        Returns
        -------
        BidiComponentResult
            A result object containing both a DeltaGenerator and the component's state,
            supporting both .property and ["dictionary"] access patterns for the state values.

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
            state_values = {"value": default}
            # Create a mock DeltaGenerator for non-context scenarios
            return BidiComponentResult(self.dg, state_values)

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

        # Parse callbacks using the new on_{state_name}_change pattern
        handlers: dict[str, WidgetCallback] = {}
        for callback_key, callback_value in on_callbacks.items():
            if (
                callback_key.startswith("on_")
                and callback_key.endswith("_change")
                and callable(callback_value)
            ):
                # Extract event name: on_foo_change -> foo
                event_name = callback_key[
                    3:-7
                ]  # Remove "on_" prefix and "_change" suffix
                if event_name:  # Ensure we have a valid event name
                    handlers[event_name] = callback_value

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

        # Use the generic widget registration – multi-event callbacks are now
        # handled centrally in SessionState.
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

        # Extract state values from the component state (it is already a mapping
        # produced by the deserializer above).
        state_dict: dict[str, Any] = {}
        if isinstance(component_state.value, dict):
            state_dict = component_state.value  # type: ignore[assignment]

        # Return BidiComponentResult with delta generator and state values
        return BidiComponentResult(self.dg, state_dict)

    @property
    def dg(self) -> DeltaGenerator:
        """Get our DeltaGenerator."""
        return cast("DeltaGenerator", self)
