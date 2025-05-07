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

with st.echo():
    HTML_FORM = """
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

    def my_component_with_paths(
        js: str | Path | None,
        html: str | None = None,
        css: str | Path | None = None,
    ):
        out = st.components.v2.component(
            name="my_component",
            html=html,
            js=js,
            css=css,
            key="my_component_1",
        )

        return out

    my_component_with_paths(
        html=HTML_FORM,
        js=Path(__file__).parent / "index.js",
        css=Path(__file__).parent / "my_styles.css",
    )
