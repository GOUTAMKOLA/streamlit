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

import inspect
from typing import TYPE_CHECKING, Any

from streamlit.components.v2.component_registry import BidiComponentDefinition
from streamlit.components.v2.get_bidi_component_registry import (
    get_bidi_component_registry,
)

if TYPE_CHECKING:
    from pathlib import Path
    from types import FrameType

    from streamlit.components.v2.bidi_component import BidiComponentState
    from streamlit.runtime.state.common import WidgetCallback


def component(
    name: str,
    *,
    html: str | None = None,
    css: str | Path | None = None,
    js: str | Path | None = None,
    isolate_styles: bool = True,
    key: str | None = None,
    default: Any = None,
    on_change: WidgetCallback | None = None,
    data: Any | None = None,
    **kwargs: Any,
) -> BidiComponentState:
    """Register and render a bidirectional component immediately."""
    import streamlit as st

    # Get our stack frame.
    current_frame: FrameType | None = inspect.currentframe()
    if current_frame is None:
        raise RuntimeError("Failed to get current frame")

    # Get the stack frame of our calling function.
    caller_frame = current_frame.f_back
    if caller_frame is None:
        raise RuntimeError("Failed to get caller frame")

    registry = get_bidi_component_registry()
    registry.register(
        BidiComponentDefinition(
            # TODO: Build a module name by sharing code with v1 (_get_module_name)
            # to prevent collisions
            name=name,
            html=html,
            css=css,
            js=js,
            isolate_styles=isolate_styles,
        )
    )

    return st.bidi_component(
        name,
        key=key,
        default=default,
        on_change=on_change,
        data=data,
        **kwargs,
    )
