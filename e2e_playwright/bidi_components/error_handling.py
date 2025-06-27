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
from typing import Any

import streamlit as st

st.header("Custom Component with incorrect JS")

with st.echo():

    def incorrect_js_component() -> Any:
        component = st.components.v2.component(
            "incorrectJsComponent",
            html="""<h1>The JS is incorrect</h1>""",
            js="""
                function Foo() {
                    // I am some JS without a default export
                }
            """,
        )

        return component()

    incorrect_js_component()


st.header("Custom Component with incorrect CSS path")

with st.echo():

    def incorrect_css_path_component() -> Any:
        component = st.components.v2.component(
            "incorrectCssPathComponent",
            html="""<h1>The CSS path is incorrect</h1>""",
            css=Path(__file__).parent / "incorrect_css_path.css",
        )

        return component()

    incorrect_css_path_component()
