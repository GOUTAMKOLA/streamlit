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

import streamlit as st

DEFAULT_JS_CODE = """export default function(component) {
  console.log("I am a bidi component", component)

  const { parentElement } = component

  const form = parentElement.querySelector("form")
  const handleSubmit = (event) => {
    event.preventDefault()
    console.log("Form submitted")
  }

  form.addEventListener("submit", handleSubmit)

  return () => {
    console.log("Cleaning up")
    form.removeEventListener("submit", handleSubmit)
  }
}
"""

DEFAULT_HTML_CODE = """<div>
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

DEFAULT_CSS_CODE = """div {
  color: red;
}
"""

st.write("# Bidi Component Editor")

# Create a form for editing the component code
with st.form("bidi_editor"):
    js_code = st.text_area("JavaScript Code", DEFAULT_JS_CODE, height=200)
    html_code = st.text_area("HTML Code", DEFAULT_HTML_CODE, height=200)
    css_code = st.text_area("CSS Code", DEFAULT_CSS_CODE, height=200)
    isolate_styles = st.checkbox("Isolate Styles", value=True)
    submit_button = st.form_submit_button("Update Component")

st.bidi_component(
    js=js_code,
    html=html_code,
    css=css_code,
    isolate_styles=isolate_styles,
)
