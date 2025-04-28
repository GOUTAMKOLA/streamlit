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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def component(
    name: str,
    html: str | None = None,
    css: str | Path | None = None,
    js: str | Path | None = None,
) -> None:
    """Register a bidirectional component.

    This function registers a bidirectional component in the component registry.
    The component can then be used in Streamlit apps via st.bidi_component.

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
    from streamlit import get_bidi_component_registry

    registry = get_bidi_component_registry()
    registry.register(name, html=html, css=css, js=js)
