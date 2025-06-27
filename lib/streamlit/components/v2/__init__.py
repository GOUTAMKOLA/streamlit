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
import os

# Used at runtime for caller inspection - must be imported outside TYPE_CHECKING.
from typing import TYPE_CHECKING, Any, Callable

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


def _get_module_name(caller_frame: FrameType) -> str:
    """Return the fully-qualified module name for the given *caller* frame.

    Mirrors the behaviour of ``streamlit.components.v1._get_module_name`` so
    that Components V1 and V2 share a consistent key-construction strategy.

    If the caller is the ``__main__`` module (e.g. when a script is executed
    directly via ``python my_component.py``) we fall back to the basename of
    the file without the ``.py`` extension. This ensures deterministic and
    descriptive component keys regardless of the execution context.
    """

    # Get the caller's module. ``inspect.getmodule`` returns ``None`` for
    # built-in or dynamically created modules which should never be the case
    # for user code that declares a component.
    module = inspect.getmodule(caller_frame)
    if module is None:
        raise RuntimeError(
            "Unable to determine calling module for component declaration."
        )

    module_name: str = module.__name__

    # When the caller is the top-level entry-point executed as a script the
    # module name is "__main__". We replace it with the filename (sans the
    # .py suffix) so that each script still gets a unique namespace.
    if module_name == "__main__":
        file_path = inspect.getfile(caller_frame)
        filename = os.path.basename(file_path)
        module_name, _ = os.path.splitext(filename)

    return module_name


def component(
    name: str,
    *,
    html: str | None = None,
    css: str | Path | None = None,
    js: str | Path | None = None,
) -> Callable[
    ...,  # positional args prohibited; enforce keyword-only at call-time
    BidiComponentResult,
]:
    """Register a bidirectional component and return a callable to mount it.

    Parameters
    ----------
    name : str
        A short, descriptive identifier for the component.
    html : str or None
        Inline HTML markup for the component root.
    css : str, Path, or None
        Inline CSS or path to a ``.css`` file.
    js : str, Path, or None
        Inline JavaScript or path to a ``.js`` file.

    Returns
    -------
    Callable[..., BidiComponentResult]
        A function that, when called inside a Streamlit script, mounts the
        component and returns its state as a ``BidiComponentResult``.
    """

    # Inspect the *call-site* to derive the caller's module and build a fully
    # qualified component key in the form ``<module_name>.<name>``. This mirrors
    # the behavior of Components V1 and prevents cross-module name collisions.

    current_frame: FrameType | None = inspect.currentframe()
    if current_frame is None:
        raise RuntimeError("Unable to inspect current frame for component declaration.")

    caller_frame = current_frame.f_back
    if caller_frame is None:
        raise RuntimeError(
            "Unable to determine caller frame for component declaration."
        )

    module_name = _get_module_name(caller_frame)
    component_key = f"{module_name}.{name}"

    registry = get_bidi_component_registry()
    registry.register(
        BidiComponentDefinition(
            name=component_key,
            html=html,
            css=css,
            js=js,
        )
    )

    # The inner callable that mounts the component.
    def _mount_component(
        *,
        key: str | None = None,
        data: Any | None = None,
        width: Width = "stretch",
        height: Height = "content",
        isolate_styles: bool = True,
        **on_callbacks: WidgetCallback | None,
    ) -> BidiComponentResult:
        """
        Parameters
        ----------
        name : str
            The *logical* name passed to ``declare_component`` (e.g. ``"slider"``).
            The helper will automatically resolve this to the fully-qualified
            registry key (``<module>.<name>``) created at declaration time.
        isolate_styles : bool
            Whether to sandbox the component styles in a shadow-root. Defaults to
            True.
        key : str or None
            An optional string to use as the unique key for the component.
        data : Any or None
            Data to pass to the component (JSON-serializable).
        width : Width
            The width of the component.
        height : Height
            The height of the component.
        **on_callbacks : WidgetCallback
            Callback functions for handling component events. Use pattern
            on_{state_name}_change (e.g., on_click_change, on_value_change).

        Returns
        -------
        BidiComponentResult
            A dictionary-like object representing the component's state.
        """
        import streamlit as st

        return st.bidi_component(
            component_key,
            key=key,
            data=data,
            width=width,
            height=height,
            isolate_styles=isolate_styles,
            **on_callbacks,
        )

    return _mount_component


__all__ = ["component"]
