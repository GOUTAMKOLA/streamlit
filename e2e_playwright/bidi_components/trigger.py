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

import time
from typing import TYPE_CHECKING, Any, Callable

import streamlit as st

if TYPE_CHECKING:
    from streamlit.components.v2.bidi_component import BidiComponentState


st.header("Bidi Component with Trigger")


JS_CODE = """
export default function(component) {
  console.log("I am a bidi component", component)

  const { parentElement, setStateValue, setTriggerValue } = component

  const handleClick = () => {
    setTriggerValue("clicked", true)
  }

  const handleClick2 = () => {
    setTriggerValue("clicked2", true)
  }

  parentElement.addEventListener("click", handleClick)
  parentElement.addEventListener("click", handleClick2)

  return () => {
    console.log("Cleaning up")
    parentElement.removeEventListener("click", handleClick)
    parentElement.removeEventListener("click", handleClick2)
  }
}
"""

HTML_CODE = """
<div>
<button>Click me</button>
<button>Click me 2</button>
</div>
"""


def my_component(
    *,
    key: str | None = None,
    data: Any | None = None,
    on_click: Callable | None = None,
    on_click2: Callable | None = None,
) -> BidiComponentState:
    out = st.components.v2.component(
        name="my_component",
        js=JS_CODE,
        html=HTML_CODE,
        isolate_styles=True,
        key=key,
        data=data,
        on_clicked_change=on_click,
        on_clicked2_change=on_click2,
    )
    return out


if "click_count" not in st.session_state:
    st.session_state.click_count = 0

if "click_count2" not in st.session_state:
    st.session_state.click_count2 = 0

if "last_on_click_processed" not in st.session_state:
    st.session_state.last_on_click_processed = None

if "last_on_click2_processed" not in st.session_state:
    st.session_state.last_on_click2_processed = None


def handle_click():
    print("Clicked")
    st.session_state.click_count += 1
    st.session_state.last_on_click_processed = time.strftime("%H:%M:%S")


def handle_click2():
    print("Clicked 2")
    st.session_state.click_count2 += 1
    st.session_state.last_on_click2_processed = time.strftime("%H:%M:%S")


result = my_component(
    key="my_component_1",
    on_click=handle_click,
    on_click2=handle_click2,
)

st.write(f"Result: {result}")
st.write(f"Click count: {st.session_state.click_count}")
st.write(
    f"Last on_click callback processed at: {st.session_state.last_on_click_processed}"
)


st.write(f"Click count 2: {st.session_state.click_count2}")
st.write(
    f"Last on_click2 callback processed at: {st.session_state.last_on_click2_processed}"
)


is_clicked = st.button("Click me")

if is_clicked:
    st.write("Button was clicked")
