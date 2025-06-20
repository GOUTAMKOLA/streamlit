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

"""Behavioural tests for the make_trigger_id helper.

The helper concatenates a component's base id with an event name using the
shared EVENT_DELIM constant ("__"). It must also guard against delimiter
collisions in either the base id or the event name.
"""

from __future__ import annotations

import pytest

from streamlit.components.v2.bidi_component import make_trigger_id
from streamlit.errors import StreamlitAPIException


@pytest.mark.parametrize(
    ("base", "event", "expected"),
    [
        ("comp", "click", "comp__click"),
        ("component123", "change", "component123__change"),
        ("Δelta", "🚀", "Δelta__🚀"),  # Unicode should be preserved
    ],
)
def test_happy_path(base: str, event: str, expected: str):
    assert make_trigger_id(base, event) == expected


def test_idempotency():
    base, event = "foo", "bar"
    first = make_trigger_id(base, event)
    second = make_trigger_id(base, event)
    assert first == second == "foo__bar"


def test_rejects_delimiter_in_base_or_event():
    with pytest.raises(StreamlitAPIException):
        make_trigger_id("bad__base", "click")

    with pytest.raises(StreamlitAPIException):
        make_trigger_id("base", "bad__event")
