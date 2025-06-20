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

"""Unit tests for the EVENT_DELIM constant used by Bidi Components.

These tests act as an executable specification for the shared delimiter
that separates a component's *base widget id* from its *event* suffix.
"""

from __future__ import annotations

from streamlit.components.v2.bidi_component import EVENT_DELIM

MODULE_PATH = "streamlit.components.v2.bidi_component"


def test_event_delim_constant_exists_and_matches_should_be_double_underscore():
    assert EVENT_DELIM == "__", (
        f"EVENT_DELIM must be set to the string '__'. Found {EVENT_DELIM!r} instead."
    )
