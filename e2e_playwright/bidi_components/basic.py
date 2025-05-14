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
    from lib.streamlit.components.v2.bidi_component import BidiComponentState

st.header("Static icon component (inline, no JS framework)")

st.write(
    "Taken from the [Product Spec](https://www.notion.so/snowflake-corp/Latest-Product-Spec-2840a4c245e84ba4a921d7122a2209b8?pvs=4#3aa0b75f1b4946e89e16283766fabe63)"
)

with st.echo():

    def emoji_icon(emoji: str) -> BidiComponentState:
        component_name = "emojiIconComponent"

        out = st.components.v2.component(
            component_name,
            html=f"""
                <h1 class="largeIcon-{component_name}">{emoji}</h1>
            """,
            # It's a good idea to put the component_name in CSS classes
            # in order to avoid leaking the class to other parts of the app.
            # Alternatively, you could set isolate_styles=True
            css=f"""
                .largeIcon-{component_name} {{
                    font-size: 3rem;
                    padding: 0;
                    margin: 0;
                }}
            """,
        )

        return out

    emoji_icon("🚀")


st.divider()

st.header("Icon component with pure-JS click event (inline, no JS framework)")

st.write(
    "Taken from the [Product Spec](https://www.notion.so/snowflake-corp/Latest-Product-Spec-2840a4c245e84ba4a921d7122a2209b8?pvs=4#17b7170bb41680d2b5c1c4cb4dea0503)"
)

with st.echo():

    def emoji_icon(emoji: str) -> BidiComponentState:
        component_name = "emojiIconComponent2"

        out = st.components.v2.component(
            component_name,
            html=f"""
                <h1 class="largeIcon-{component_name}">{emoji}</h1>
            """,
            # It's a good idea to put the component_name in CSS classes
            # in order to avoid leaking the class to other parts of the app.
            # Alternatively, you could set isolate_styles=True
            css=f"""
                .largeIcon-{component_name} {{
                    font-size: 3rem;
                    padding: 0;
                    margin: 0;
                }}
            """,
            # Just to show how we could add JS to the above, let's attach a
            # click listener to the emoji above to display an alert window.
            js="""
                export default function main(component) {
                    component.parentElement.querySelector("h1").addEventListener(
                        "click",
                        () => alert("Clicked!"),
                    )
                }
            """,
        )

        return out

    emoji_icon("🚀")

st.divider()


st.header("Bidi Component")

with st.echo():
    JS_CODE = """
export default function(component) {
  console.log("I am a bidi component", component)

  const { parentElement, onChange, onClick } = component

  const form = parentElement.querySelector("form")
  const handleSubmit = (event) => {
    event.preventDefault()
    const formValues = {
      range: event.target.range.value,
      text: event.target.text.value,
    }
    console.log("Form submitted with values", formValues)
    onChange(formValues)
  }

  form.addEventListener("submit", handleSubmit)

  parentElement.addEventListener("click", onClick, { capture: true })

  return () => {
    console.log("Cleaning up")
    form.removeEventListener("submit", handleSubmit)
    parentElement.removeEventListener("click", onClick, { capture: true })
  }
}
"""

    HTML_CODE = """
<div>
  <h1>Hello World</h1>
  <form>
    <label for="range">Range</label>
    <input type="range" id="range" min="0" max="100" value="50" />
    <label for="text">Text</label>
    <input type="text" id="text" value="Text input" />
    <button type="submit">Submit form</button>
  </form>
</div>
"""

    CSS_CODE = """
div {
  color: red;
}
"""

    def my_component(
        *,
        key: str | None = None,
        data: Any | None = None,
        on_change: Callable | None = None,
        on_click: Callable | None = None,
    ) -> BidiComponentState:
        out = st.components.v2.component(
            name="my_component",
            js=JS_CODE,
            html=HTML_CODE,
            css=CSS_CODE,
            isolate_styles=True,
            key=key,
            data=data,
            on_change=on_change,
            on_click=on_click,
        )
        return out

    if "click_count" not in st.session_state:
        st.session_state.click_count = 0

    if "last_on_click_processed" not in st.session_state:
        st.session_state.last_on_click_processed = None

    def handle_click():
        st.session_state.click_count += 1
        st.session_state.last_on_click_processed = time.strftime("%H:%M:%S")

    if "last_on_change_processed" not in st.session_state:
        st.session_state.last_on_change_processed = None

    def handle_change():
        print("Value changed")
        st.session_state.last_on_change_processed = time.strftime("%H:%M:%S")

    result = my_component(
        key="my_component_1",
        data={"label": "Some data from python"},
        on_change=handle_change,
        on_click=handle_click,
    )

    st.write(f"Result: {result}")
    if st.session_state.last_on_change_processed:
        st.write(
            f"Last on_change callback processed at: {st.session_state.last_on_change_processed}"
        )
    if st.session_state.last_on_click_processed:
        st.write(
            f"Last on_click callback processed at: {st.session_state.last_on_click_processed}"
        )

    st.write(f"Click count: {st.session_state.click_count}")
