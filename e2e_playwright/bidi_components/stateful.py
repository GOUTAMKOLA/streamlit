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

from typing import TYPE_CHECKING, Any

import streamlit as st

if TYPE_CHECKING:
    from streamlit.components.v2.bidi_component import BidiComponentResult
    from streamlit.elements.lib.layout_utils import Height, Width
    from streamlit.runtime.state.common import WidgetCallback

st.header("Bidi Component")

JS_CODE = """
export default function(component) {
  const { parentElement, setStateValue } = component

  const handleRangeChange = (event) => {
    setStateValue("range", event.target.value)
  }

  const handleTextChange = (event) => {
    setStateValue("text", event.target.value)
  }

  const rangeInput = parentElement.querySelector("#range")
  rangeInput.addEventListener("change", handleRangeChange)

  const textInput = parentElement.querySelector("#text")
  textInput.addEventListener("input", handleTextChange)

  return () => {
    rangeInput.removeEventListener("change", handleRangeChange)
    textInput.removeEventListener("input", handleTextChange)
  }
}
"""

HTML_CODE = """
<div>
  <label for="range">Range</label>
  <input type="range" id="range" min="0" max="100" value="50" />
  <label for="text">Text</label>
  <input type="text" id="text" value="Text input" />
</div>
"""


def my_component(
    *,
    key: str | None = None,
    data: Any | None = None,
    on_range_change: WidgetCallback | None = None,
    on_text_change: WidgetCallback | None = None,
    width: Width | None = None,
    height: Height | None = None,
) -> BidiComponentResult:
    out = st.components.v2.component(
        name="my_component",
        js=JS_CODE,
        html=HTML_CODE,
        isolate_styles=True,
        key=key,
        data=data,
        on_range_change=on_range_change,
        on_text_change=on_text_change,
        width=width,
        height=height,
    )
    return out


if "range_change_count" not in st.session_state:
    st.session_state.range_change_count = 0
if "text_change_count" not in st.session_state:
    st.session_state.text_change_count = 0


def handle_range_change():
    st.session_state.range_change_count += 1


def handle_text_change():
    st.session_state.text_change_count += 1


result = my_component(
    key="my_component_1",
    on_range_change=handle_range_change,
    on_text_change=handle_text_change,
)

st.write(f"Result: {result}")
st.write(f"Range change count: {st.session_state.range_change_count}")
st.write(f"Text change count: {st.session_state.text_change_count}")


is_clicked = st.button("st.button trigger")

if is_clicked:
    st.write("st.button was clicked")
