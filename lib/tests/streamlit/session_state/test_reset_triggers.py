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

"""Unit tests for SessionState._reset_triggers with json_trigger_value support."""

from __future__ import annotations

import json

from streamlit.runtime.state.session_state import SessionState, Value, WidgetMetadata


def _dummy_serializer(x):
    return x


def _dummy_deserializer(x):
    return x


def test_json_trigger_value_gets_reset():
    """Ensure json_trigger_value fields are cleared to None after _reset_triggers."""
    ss = SessionState()

    widget_id = "comp__event"

    meta = WidgetMetadata(
        id=widget_id,
        deserializer=_dummy_deserializer,
        serializer=_dummy_serializer,
        value_type="json_trigger_value",
        callbacks=None,
        callback_args=None,
        callback_kwargs=None,
        fragment_id=None,
    )

    # Register metadata and set initial trigger payload
    ss._set_widget_metadata(meta)
    payload = {"clicked": True}
    ss._new_widget_state[widget_id] = Value(json.dumps(payload))
    ss._old_state[widget_id] = payload

    # Act
    ss._reset_triggers()

    # Assert: value should now be None in both new and old state mappings
    assert ss._new_widget_state[widget_id] is None
    assert ss._old_state[widget_id] is None
