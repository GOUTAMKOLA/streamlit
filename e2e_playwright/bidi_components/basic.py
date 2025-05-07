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
from typing import Any, Callable

import streamlit as st

# Initialize session state to store component code
if "js_code" not in st.session_state:
    st.session_state.js_code = """export default function(component) {
  console.log("I am a bidi component", component)

  const { parentElement, onChange } = component

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

  return () => {
    console.log("Cleaning up")
    form.removeEventListener("submit", handleSubmit)
  }
}"""

if "html_code" not in st.session_state:
    st.session_state.html_code = """<div>
  <h1>Hello World</h1>
  <form>
    <label for="range">Range</label>
    <input type="range" id="range" min="0" max="100" value="50" />
    <label for="text">Text</label>
    <input type="text" id="text" value="Text input" />
    <button type="submit">Submit form</button>
  </form>
</div>"""

if "css_code" not in st.session_state:
    st.session_state.css_code = """div {
  color: red;
}"""

if "isolate_styles" not in st.session_state:
    st.session_state.isolate_styles = True


def my_component(
    *,
    key: str | None = None,
    data: Any | None = None,
    on_change: Callable | None = None,
):
    print(f"my_component called with key={key}, on_change={on_change}")
    # Get a callable function that renders the component
    render_component = st.components.v2.component(
        # For demo purposes, we'll use a random name to avoid collisions
        # and to ensure that the component is re-created when the form is
        # submitted.
        # name=f"my_component-{random.randint(0, 1000000)}",
        name="my_component",
        js=st.session_state.js_code,
        html=st.session_state.html_code,
        css=st.session_state.css_code,
        isolate_styles=st.session_state.isolate_styles,
    )

    # Call the function to render the component
    out = render_component(
        key=key,
        data=data,
        on_change=on_change,
    )
    return out


def update_component():
    # Update session state with form values
    st.session_state.js_code = st.session_state.js_editor
    st.session_state.html_code = st.session_state.html_editor
    st.session_state.css_code = st.session_state.css_editor
    st.session_state.isolate_styles = st.session_state.isolate_styles_checkbox


st.write("# Bidi Component Editor")

# Create a form for editing the component code
st.write("## Edit Component")
with st.form("bidi_editor", clear_on_submit=False):
    st.text_area(
        "JavaScript Code", st.session_state.js_code, height=200, key="js_editor"
    )
    st.text_area("HTML Code", st.session_state.html_code, height=200, key="html_editor")
    st.text_area("CSS Code", st.session_state.css_code, height=200, key="css_editor")
    st.checkbox(
        "Isolate Styles",
        value=st.session_state.isolate_styles,
        key="isolate_styles_checkbox",
    )
    submit_button = st.form_submit_button("Update Component", on_click=update_component)


if "value" not in st.session_state:
    st.session_state.value = 1

if "last_callback_time" not in st.session_state:
    st.session_state.last_callback_time = None


def handle_change():
    print("Value changed")
    st.session_state.value += 1
    st.session_state.last_callback_time = time.strftime("%H:%M:%S")
    print(f"Value incremented to {st.session_state.value}")


st.write("## Component Instances")

result = my_component(
    key="my_component_1",
    data={"label": "Some data from python"},
    on_change=handle_change,
)

st.write(f"Counter value: {st.session_state.value}")
if st.session_state.last_callback_time:
    st.write(f"Last callback processed at: {st.session_state.last_callback_time}")
