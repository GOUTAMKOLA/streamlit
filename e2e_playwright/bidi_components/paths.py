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

from pathlib import Path

import streamlit as st

if "rerun_count" not in st.session_state:
    st.session_state.rerun_count = 0


def my_component_with_paths(
    js: str | Path | None, html: str | None = None, css: str | Path | None = None
):
    # Get a callable function that renders the component
    render_component = st.components.v2.component(
        name="my_component",
        html="<div>hello</div>",
        js="export default function(component) {}",
        key="my_component_1",
    )

    return render_component


HTML_FORM = """<div>
  <h1>Hello World</h1>
  <form>
    <label for="range">Range</label>
    <input type="range" id="range" min="0" max="100" value="50" />
    <label for="text">Text</label>
    <input type="text" id="text" value="Text input" />
    <button type="submit">Submit form</button>
  </form>
</div>"""

my_component_with_paths(
    js=Path(__file__).parent / "example" / "index.js",
    html=HTML_FORM,
    css=Path(__file__).parent / "example" / "my_styles.css",
)


def rerun():
    # Do something that causes the component to re-render
    st.session_state.rerun_count += 1


st.button("Update Component", on_click=rerun)

st.write(f"Rerun count: {st.session_state.rerun_count}")
