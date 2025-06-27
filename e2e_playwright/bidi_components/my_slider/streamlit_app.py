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
from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from streamlit.components.v2.bidi_component import BidiComponentResult
    from streamlit.runtime.state.common import WidgetCallback

st.header("Custom slider component (no JS framework)")

st.write(
    "Taken from the [Product Spec](https://www.notion.so/snowflake-corp/Latest-Product-Spec-2840a4c245e84ba4a921d7122a2209b8?pvs=4#071968bcb9ea49789292d533f5ad3867)"
)

with st.echo():
    if "value" not in st.session_state:
        st.session_state["value"] = 50

    def custom_slider(
        label: str | None = None,
        min: int = 0,
        max: int = 100,
        value: int | None = None,
        callback: WidgetCallback | None = None,
        key: str | None = None,
    ) -> BidiComponentResult:
        if value is None:
            value = min

        component = st.components.v2.component(
            "sliderComponent", js=Path(__file__).parent / "index.js"
        )

        return component(
            data={"label": label, "min": min, "max": max, "value": value},
            # TODO: Fix this to utilize the new callback API naming convention
            on_change=callback,
            key=key,
        )

    def handle_change():
        st.session_state["value"] = st.session_state["value"] + 1

    value = custom_slider(
        label="My slider",
        min=0,
        max=100,
        value=50,
        callback=handle_change,
        key="my_slider",
    )

    st.write(
        f"Value from component: {value}, session state: {st.session_state['value']}"
    )
