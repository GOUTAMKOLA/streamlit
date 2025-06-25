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
from typing import TYPE_CHECKING, Any, Final, TypedDict, cast

from streamlit.elements.lib.form_utils import current_form_id
from streamlit.elements.lib.policies import check_cache_replay_rules
from streamlit.elements.lib.utils import compute_and_register_element_id, to_key
from streamlit.errors import StreamlitAPIException

# Assuming protos are compiled and BidiComponentInstance is available:
from streamlit.proto.BidiComponent_pb2 import BidiComponent as BidiComponentProto
from streamlit.runtime.metrics_util import gather_metrics
from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx
from streamlit.runtime.state import register_widget
from streamlit.util import AttributeDictionary

if TYPE_CHECKING:
    # Define DeltaGenerator for type checking the dg property
    from streamlit.delta_generator import DeltaGenerator
    from streamlit.runtime.state.common import WidgetCallback


INTERNAL_COMPONENT_NAME = "bidi_component"

# Shared constant that delimits the base widget id from the event suffix.
# This value **must** stay in sync with its TypeScript counterpart defined in
# `frontend/lib/src/components/widgets/BidiComponent/constants.ts`.
EVENT_DELIM: Final[str] = "__"


def make_trigger_id(base: str, event: str) -> str:
    """Construct the per-event *trigger widget* identifier.

    The widget id for a trigger is derived from the *base* component id plus
    an *event* name. We join those two parts with :pydata:`EVENT_DELIM` and
    perform a couple of validations so that downstream logic can always split
    the identifier unambiguously.

    Parameters
    ----------
    base : str
        The unique, framework-assigned id of the component instance.
    event : str
        The event name as provided by either the frontend or the developer
        (e.g. "click", "change").

    Returns
    -------
    str
        The composite widget id in the form ``"{base}__{event}"`` where
        ``__`` is the delimiter.

    Raises
    ------
    ValueError
        If either *base* or *event* already contains the delimiter sequence.
    """

    if EVENT_DELIM in base:
        raise StreamlitAPIException(
            "Base component id must not contain the delimiter sequence"
        )
    if EVENT_DELIM in event:
        raise StreamlitAPIException(
            "Event name must not contain the delimiter sequence"
        )

    return f"{base}{EVENT_DELIM}{event}"


# ----------------------------------------------------------------------
# Public state typing
# ----------------------------------------------------------------------


class BidiComponentState(TypedDict, total=False):
    """
    The schema for the BidiComponent state.

    The state is stored in a dictionary-like object that supports both key and
    attribute notation. States cannot be programmatically changed or set through
    Session State.

    Attributes
    ----------
    value : dict[str, Any]
        The current value of the component instance returned from the frontend,
        or the default value if not yet set.
    """

    value: dict[str, Any]


class BidiComponentResult(AttributeDictionary):
    """Rich return object for ``st.bidi_component``.

    It behaves like a regular :class:`dict` *and* allows attribute-style
    access to its keys, mirroring the behaviour of
    :class:`streamlit.util.AttributeDictionary`. In addition, it surfaces the
    :pyclass:`~streamlit.delta_generator.DeltaGenerator` instance responsible
    for rendering the component via the dedicated :pyattr:`delta_generator`
    property.
    """

    def __init__(
        self,
        dg: DeltaGenerator,
        state_vals: dict[str, Any] | None = None,
        trigger_vals: dict[str, Any] | None = None,
    ) -> None:
        if state_vals is None:
            state_vals = {}
        if trigger_vals is None:
            trigger_vals = {}

        # We store the DeltaGenerator under a dedicated key so that callers can
        # access it via both attribute and mapping syntax without colliding
        # with user-supplied state or trigger names.
        super().__init__(
            {
                "delta_generator": dg,
                # The order here matters, because all stateful values will
                # always be returned, but trigger values may be transient.
                **trigger_vals,
                **state_vals,
            }
        )

    # Expose a typed property for convenient IDE auto-completion.
    @property
    def delta_generator(self) -> DeltaGenerator:
        """Return the :class:`~streamlit.delta_generator.DeltaGenerator` that
        rendered this component.
        """
        return cast("DeltaGenerator", self["delta_generator"])


@dataclass
class BidiComponentSerde:
    """Serialization/deserialization logic for BidiComponent.

    Assumes communication via JSON strings.
    """

    def deserialize(self, ui_value: str | dict[str, Any] | None) -> BidiComponentState:
        """Deserialize the state from the frontend.

        Args:
            ui_value: The JSON string received from the frontend.

        Returns
        -------
            The deserialized state wrapped in an AttributeDictionary.
        """
        # We always normalise the incoming JSON payload into a *dict*.
        # Any failure to decode (or an unexpected non-mapping structure)
        # results in an empty mapping so that the returned type adheres to
        # :class:`BidiComponentState`.

        deserialized_value: dict[str, Any]

        if isinstance(ui_value, dict):
            deserialized_value = ui_value
        elif ui_value is not None:
            try:
                parsed = json.loads(ui_value)
                deserialized_value = parsed if isinstance(parsed, dict) else {}
            except Exception:
                deserialized_value = {}
        else:
            deserialized_value = {}

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
        return json.dumps(value)


class BidiComponentMixin:
    """Mixin class for the bidi_component DeltaGenerator method."""

    @gather_metrics("bidi_component")
    def bidi_component(
        self,
        component_name: str,
        *args: Any,
        key: str | None = None,
        # TODO: This needs to have a better type + support Arrow
        data: Any | None = None,
        **kwargs: WidgetCallback | None,
    ) -> BidiComponentResult:
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
        **kwargs
            Keyword arguments to pass to the component.

        Returns
        -------
        BidiComponentResult
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
            state: BidiComponentState = {"value": {}}
            return BidiComponentResult(self.dg, state.get("value", {}), {})

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

        # ------------------------------------------------------------------
        # 1. Parse user-supplied callbacks
        # ------------------------------------------------------------------
        # Event-specific callbacks follow the pattern ``on_<event>_change``.
        # We deliberately *do not* support the legacy generic ``on_change``
        # or ``on_<event>`` forms.
        callbacks_by_event: dict[str, WidgetCallback] = {}
        for kwarg_key, kwarg_value in list(kwargs.items()):
            if not callable(kwarg_value):
                continue

            if kwarg_key.startswith("on_") and kwarg_key.endswith("_change"):
                # Preferred pattern: on_<event>_change
                event_name = kwarg_key[3:-7]  # strip prefix + suffix
            else:
                # Not an event callback we recognise - skip.
                continue

            if not event_name:
                # Malformed name like "on__change" - ignore for now.
                continue

            callbacks_by_event[event_name] = kwarg_value

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
        bidi_component_proto.form_id = current_form_id(self.dg)
        if callbacks_by_event:
            bidi_component_proto.registered_handler_names.extend(
                callbacks_by_event.keys()
            )

        # Instantiate the Serde for this component instance
        serde = BidiComponentSerde()

        # ------------------------------------------------------------------
        # 2. Register the *persistent state* widget (one per component)
        # ------------------------------------------------------------------

        # When the frontend calls `setStateValue`, it updates the component's
        # *persistent* JSON state (one per component instance). In order to
        # surface these updates to the user we attach a single "change"
        # callback to this state widget that performs a fine-grained diff and
        # only invokes the callbacks whose associated key actually changed.

        # Keep track of the previous state across callback invocations so that
        # we can detect which keys were modified. We initialise it to an empty
        # dict here and populate it with the component's current state once
        # the widget is registered (see further below).
        _prev_state: dict[str, Any] = {}

        def _on_component_state_change() -> None:
            """Dispatch state-change notifications to the *relevant* handlers.

            We compare the latest component state with the previously cached
            version and identify which top-level keys (i.e. state entries)
            actually changed. Only the callbacks that correspond to those
            keys are executed. This prevents unrelated callbacks from firing
            when their piece of state remained untouched.
            """

            nonlocal _prev_state

            # Fetch the *latest* component state from Session State instead of
            # relying on the stale ``component_state`` captured from the script
            # run in which this callback was registered. Using Session State
            # guarantees we always operate on the up-to-date value produced by
            # the most recent frontend → backend update.

            current_ctx = get_script_run_ctx()

            # If, for some unexpected reason, we don't have a script context
            # we bail early - there's nothing useful we can do.
            if current_ctx is None:
                return

            try:
                raw_val = current_ctx.session_state[computed_id]
            except KeyError:
                # The component might have been removed in the meantime. Skip.
                return

            # Extract the *inner* mapping of the state.
            current_state_dict = _unwrap_component_state(raw_val)

            # Determine which keys were added, removed or had their value
            # changed. We treat None vs missing as a change so that setting a
            # key to None still triggers its callback.
            changed_keys: set[str] = set()

            # Keys that are new or whose value differs from the previous run.
            for k, v in current_state_dict.items():
                if k not in _prev_state or _prev_state.get(k) != v:
                    changed_keys.add(k)

            # Keys that were removed.
            for k in _prev_state:
                if k not in current_state_dict:
                    changed_keys.add(k)

            # Execute the callbacks associated with the changed keys.
            for changed_key in changed_keys:
                cb = callbacks_by_event.get(changed_key)
                if cb is None:
                    continue
                cb()

            # Update the cached copy for the next comparison.
            _prev_state = dict(current_state_dict)

        component_state = register_widget(
            bidi_component_proto.id,
            deserializer=serde.deserialize,
            serializer=serde.serialize,
            ctx=ctx,
            callbacks={"change": _on_component_state_change}
            if callbacks_by_event
            else None,
            value_type="json_value",
        )

        # Prime `_prev_state` with the *current* component state so that the
        # very first diff performed inside `_on_component_state_change` (i.e.
        # after the user interacts with the component for the first time)
        # correctly reflects only the keys that actually changed.
        # `component_state.value` may include the additional ``{"value": ...}``
        # wrapper injected by our Serde. To ensure we treat individual *state
        # keys* consistently we unwrap one level if that structure is
        # detected.

        _initial_raw_val = component_state.value  # AttributeDictionary or primitive

        _prev_state = _unwrap_component_state(_initial_raw_val)

        # ------------------------------------------------------------------
        # 3. Register *trigger* widgets - one per event
        # ------------------------------------------------------------------
        trigger_vals: dict[str, Any] = {}

        for evt_name, evt_cb in callbacks_by_event.items():
            trig_id = make_trigger_id(computed_id, evt_name)

            trig_state = register_widget(
                trig_id,
                deserializer=lambda s: json.loads(s) if s else None,
                serializer=lambda v: json.dumps(v),
                ctx=ctx,
                callbacks={"change": evt_cb} if evt_cb is not None else None,
                value_type="json_trigger_value",
            )

            trigger_vals[evt_name] = trig_state.value

        # Note: We intentionally do not inspect SessionState for additional
        # trigger widget IDs here because doing so can raise KeyErrors when
        # widgets are freshly registered but their values haven't been
        # populated yet. Only the triggers explicitly registered above are
        # included in the result object.

        # ------------------------------------------------------------------
        # 4. Enqueue proto and assemble the result object
        # ------------------------------------------------------------------
        self.dg._enqueue(INTERNAL_COMPONENT_NAME, bidi_component_proto)

        # `component_state.value` is expected to be a mapping-like object (via
        # our Serde), but we defensively normalise it into a plain `dict` so
        # that users never observe AttributeDictionary instances nested inside
        # the result.
        state_vals = _unwrap_component_state(component_state.value)

        return BidiComponentResult(self.dg, state_vals, trigger_vals)

    @property
    def dg(self) -> DeltaGenerator:
        """Get our DeltaGenerator."""
        return cast("DeltaGenerator", self)


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------


def _unwrap_component_state(raw_state: Any) -> dict[str, Any]:
    """Return the inner mapping of a *valid* :class:`BidiComponentState`.

    A valid component state **must** be a mapping that contains exactly one key:
    ``"value"``, whose associated value is itself a mapping holding the actual
    per-key state entries produced by the frontend.

    Any other shape is considered invalid and will be treated as an empty
    mapping. This strictness ensures we never silently accept malformed data
    that could mask bugs elsewhere in the stack.

    Parameters
    ----------
    raw_state : Any
        The value retrieved from Session State.

    Returns
    -------
    dict[str, Any]
        The *inner* state mapping if the input adheres to the expected
        structure, otherwise an empty ``dict``.
    """

    if (
        isinstance(raw_state, dict)
        and set(raw_state.keys()) == {"value"}
        and isinstance(raw_state["value"], dict)
    ):
        # Shallow-copy to decouple from the original reference.
        return dict(raw_state["value"])

    # Any deviation from the expected schema is regarded as invalid.
    return {}
