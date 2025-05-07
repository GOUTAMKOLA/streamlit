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

import functools
import inspect
from typing import TYPE_CHECKING, Any, Callable

from streamlit.components.v2.component_registry import (
    BidiComponentDefinition,
    BidiComponentRegistry,
)
from streamlit.runtime.scriptrunner import get_script_run_ctx

if TYPE_CHECKING:
    from pathlib import Path
    from types import FrameType

    from streamlit.components.v2.bidi_component import BidiComponentState
    from streamlit.runtime.state.common import WidgetCallback


def get_bidi_component_registry() -> BidiComponentRegistry:
    """Get the BidiComponentRegistry for the current session."""
    ctx = get_script_run_ctx()
    if ctx is None:
        # This case should ideally not be hit in normal app execution.
        # It might occur in tests or if called from outside a script run.
        # Depending on strictness, could raise an error or return a
        # global/dummy registry if one makes sense. For now, raising an error.
        raise RuntimeError("Cannot get BidiComponentRegistry: not in a script run.")

    # Avoid circular import by importing at function call time
    from streamlit.runtime import Runtime

    if not Runtime.exists():
        raise RuntimeError("Cannot get BidiComponentRegistry: Runtime doesn't exist.")

    runtime = Runtime.instance()
    session_info = runtime._session_mgr.get_active_session_info(ctx.session_id)
    if session_info is None or session_info.session is None:
        # This would be unusual if ctx exists.
        raise RuntimeError(
            f"Cannot get BidiComponentRegistry: no active session found for id {ctx.session_id}."
        )

    return session_info.session.bidi_component_registry


def component(
    name: str,
    html: str | None = None,
    css: str | Path | None = None,
    js: str | Path | None = None,
    isolate_styles: bool = True,
) -> Callable[..., BidiComponentState]:
    """Register a bidirectional component.

    This function registers a bidirectional component in the component registry.

    Parameters
    ----------
    name : str
        A short, descriptive name for the component.
    html : str or None
        HTML content as a string.
    css : str, Path, or None
        CSS content as a string, or a path to a CSS file.
    js : str, Path, or None
        JavaScript content as a string, or a path to a JS file.
    isolate_styles : bool, default True
        Whether to isolate the component's CSS styles to avoid affecting other elements.
        Set to False if you want the component's styles to affect the entire page.

    Returns
    -------
    Callable
        A callable function that creates instances of the registered component.

    Examples
    --------
    >>> import streamlit as st
    >>>
    >>> # Register a component with HTML, CSS, and JS
    >>> def emoji_icon(emoji: str):
    ...     component_name = "emojiIconComponent"
    ...     out = st.components.v2.component(
    ...         name=component_name,
    ...         html=f"<div>{emoji}</div>",
    ...         css="div { font-size: 2em; }",
    ...     )
    ...
    ...     return out
    >>>
    >>> # Use the component in a Streamlit app
    >>> emoji_icon("🚀")
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

    # Create a wrapper function that calls st.bidi_component with the registered component name
    @functools.wraps(st.bidi_component)
    def component_instance(
        *args,
        key: str | None = None,
        default: Any = None,
        on_change: WidgetCallback | None = None,
        **kwargs,
    ) -> BidiComponentState:
        """Create an instance of the registered component.

        Parameters
        ----------
        *args
            Positional arguments to pass to the component.
        key : str or None
            An optional string to use as the unique key for the component.
        default: any or None
            The default return value for the component.
        on_change: WidgetCallback or None
            An optional callback invoked when the component's value changes.
        **kwargs
            Keyword arguments to pass to the component.

        Returns
        -------
        BidiComponentState
            The component's state.
        """
        return st.bidi_component(
            name, *args, key=key, default=default, on_change=on_change, **kwargs
        )

    return component_instance
