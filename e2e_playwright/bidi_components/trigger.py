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
from typing import TYPE_CHECKING, Any

import streamlit as st

if TYPE_CHECKING:
    from streamlit.components.v2.bidi_component import BidiComponentResult
    from streamlit.runtime.state.common import WidgetCallback

st.header("Bidi Component with Trigger")


JS_CODE = """
export default function(component) {
  const { parentElement, setTriggerValue } = component

  const handleClickFoo = () => {
    setTriggerValue("foo", true)
  }

  const handleClickBar = () => {
    setTriggerValue("bar", true)
  }

  const handleClickBoth = () => {
    setTriggerValue("foo", true)
    setTriggerValue("bar", true)
  }

  const fooButton = parentElement.querySelector("#foo-button")
  const barButton = parentElement.querySelector("#bar-button")
  const bothButton = parentElement.querySelector("#both-button")

  fooButton.addEventListener("click", handleClickFoo)
  barButton.addEventListener("click", handleClickBar)
  bothButton.addEventListener("click", handleClickBoth)

  return () => {
    fooButton.removeEventListener("click", handleClickFoo)
    barButton.removeEventListener("click", handleClickBar)
    bothButton.removeEventListener("click", handleClickBoth)
  }
}
"""

HTML_CODE = """
<div>
    <button id="foo-button">Trigger foo</button>
    <button id="bar-button">Trigger bar</button>
    <button id="both-button">Trigger both</button>
</div>
"""

_my_component = st.components.v2.component("my_component", js=JS_CODE, html=HTML_CODE)


def my_component(
    *,
    key: str | None = None,
    data: Any | None = None,
    on_foo_change: WidgetCallback | None = None,
    on_bar_change: WidgetCallback | None = None,
) -> BidiComponentResult:
    return _my_component(
        isolate_styles=True,
        key=key,
        data=data,
        on_foo_change=on_foo_change,
        on_bar_change=on_bar_change,
    )


if "foo_count" not in st.session_state:
    st.session_state.foo_count = 0

if "bar_count" not in st.session_state:
    st.session_state.bar_count = 0

if "last_on_foo_change_processed" not in st.session_state:
    st.session_state.last_on_foo_change_processed = None

if "last_on_bar_change_processed" not in st.session_state:
    st.session_state.last_on_bar_change_processed = None


def handle_foo_change():
    st.session_state.foo_count += 1
    st.session_state.last_on_foo_change_processed = time.strftime("%H:%M:%S")


def handle_bar_change():
    st.session_state.bar_count += 1
    st.session_state.last_on_bar_change_processed = time.strftime("%H:%M:%S")


result = my_component(
    key="my_component_1",
    on_foo_change=handle_foo_change,
    on_bar_change=handle_bar_change,
)

st.write(f"Result: {result}")
st.write(f"Foo count: {st.session_state.foo_count}")
st.write(
    f"Last on_foo_change callback processed at: {st.session_state.last_on_foo_change_processed}"
)


st.write(f"Bar count: {st.session_state.bar_count}")
st.write(
    f"Last on_bar_change callback processed at: {st.session_state.last_on_bar_change_processed}"
)


is_clicked = st.button("st.button trigger")

if is_clicked:
    st.write("st.button was clicked")
