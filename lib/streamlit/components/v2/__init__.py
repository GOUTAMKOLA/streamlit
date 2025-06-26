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

    from streamlit.components.v2.bidi_component import BidiComponentResult
    from streamlit.elements.lib.layout_utils import Height, Width
    from streamlit.runtime.state.common import WidgetCallback


def component(
    name: str,
    *,
    html: str | None = None,
    css: str | Path | None = None,
    js: str | Path | None = None,
    isolate_styles: bool = True,
    key: str | None = None,
    data: Any | None = None,
    width: Width = "stretch",
    height: Height = "content",
    **on_callbacks: WidgetCallback | None,
) -> BidiComponentResult:
    """Register and render a bidirectional component immediately.

    Parameters
    ----------
    name : str
        The component name for telemetry purposes.
    html : str or None
        HTML content as a string.
    css : str, Path, or None
        CSS content as a string or path to CSS file.
    js : str, Path, or None
        JavaScript content as a string or path to JS file.
    isolate_styles : bool
        Whether to isolate styles for the component. Defaults to True.
    key : str or None
        An optional string to use as the unique key for the component.
    data : Any or None
        Data to pass to the component (JSON-serializable).
    **on_callbacks : WidgetCallback
        Callback functions for handling component events. Use pattern
        on_{state_name}_change (e.g., on_click_change, on_value_change).

    Returns
    -------
    BidiComponentResult
        A dictionary-like object representing the component's state.
    """
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
        data=data,
        width=width,
        height=height,
        **on_callbacks,
    )


__all__ = ["component"]
