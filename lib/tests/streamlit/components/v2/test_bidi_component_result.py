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

"""Unit tests for :class:`streamlit.components.v2.bidi_component.BidiComponentResult`.

These tests ensure that the object correctly merges *state* and *trigger* values
while exposing the originating :pyclass:`~streamlit.delta_generator.DeltaGenerator`
via the dedicated :pyattr:`delta_generator` property.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from streamlit.components.v2.bidi_component import BidiComponentResult


def test_result_merges_state_and_trigger_values_and_exposes_dg():
    """BidiComponentResult should behave like a mapping/attribute dict and expose the dg."""

    # Arrange
    mock_dg = MagicMock(name="DeltaGeneratorMock")
    state_vals = {"foo": 123, "bar": "abc"}
    trigger_vals = {"clicked": True, "changed": {"value": 42}}

    # Act
    result = BidiComponentResult(mock_dg, state_vals, trigger_vals)

    # Assert mapping access
    assert result["foo"] == 123
    assert result["bar"] == "abc"
    assert result["clicked"] is True
    assert result["changed"] == {"value": 42}
    assert result["delta_generator"] is mock_dg

    # Assert attribute access
    assert result.foo == 123
    assert result.bar == "abc"
    assert result.clicked is True
    assert result.changed == {"value": 42}
    assert result.delta_generator is mock_dg
