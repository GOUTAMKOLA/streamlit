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
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final

from streamlit.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import MutableMapping
    from types import FrameType

_LOGGER: Final = get_logger(__name__)


def _get_caller_path() -> str:
    """Return the path of the caller's file."""
    # Get our stack frame.
    current_frame: FrameType | None = inspect.currentframe()
    if current_frame is None:
        raise RuntimeError("Unable to inspect current frame")
    # Get the stack frame of our calling function.
    caller_frame = current_frame.f_back
    # The caller of this function might itself be a helper function.
    # We want to find the actual user code that's calling.
    while caller_frame is not None:
        module = inspect.getmodule(caller_frame)
        if module is not None and module.__name__ == __name__:
            # Still in our module, go up one more level
            caller_frame = caller_frame.f_back
        else:
            break

    if caller_frame is None:
        raise RuntimeError("Unable to find caller frame")
    file_path = inspect.getfile(caller_frame)
    return file_path


@dataclass(frozen=True)
class BidiComponentDefinition:
    """Definition of a bidirectional component V2.

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
    isolate_styles : bool
        Whether to isolate styles for the component.
    """

    name: str
    html: str | None = None
    css: str | Path | None = None
    js: str | Path | None = None
    isolate_styles: bool = True
    # Store processed content and metadata
    _is_css_path: bool = field(default=False, init=False, repr=False)
    _is_js_path: bool = field(default=False, init=False, repr=False)
    _source_paths: dict[str, str] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        # Keep track of source paths for content loaded from files
        source_paths = {}

        # Store CSS and JS paths if provided
        is_css_path, css_path = self._is_file_path(self.css)
        is_js_path, js_path = self._is_file_path(self.js)

        if css_path:
            source_paths["css"] = os.path.dirname(css_path)
        if js_path:
            source_paths["js"] = os.path.dirname(js_path)

        object.__setattr__(self, "_is_css_path", is_css_path)
        object.__setattr__(self, "_is_js_path", is_js_path)
        object.__setattr__(self, "_source_paths", source_paths)

        # Validate that at least one content type is provided
        if not self.html and not self.js and not self.css:
            raise ValueError(
                "BidiComponentDefinition must have at least one of html, css, or js."
            )

    def _is_file_path(self, content: str | Path | None) -> tuple[bool, str | None]:
        """Determine if the content is a file path.

        Returns
        -------
            A tuple (is_path, path) where:
            - is_path: True if the content is a file path
            - path: The absolute path to the file if content is a path, otherwise None
        """
        if content is None:
            return False, None

        if isinstance(content, Path):
            content_str = str(content)
            # Path objects are always treated as file paths
            try:
                if os.path.isabs(content_str):
                    abs_path = content_str
                else:
                    # Relative path, make it relative to the caller's file
                    caller_dir = os.path.dirname(_get_caller_path())
                    abs_path = os.path.abspath(os.path.join(caller_dir, content_str))

                if not os.path.exists(abs_path):
                    raise ValueError(f"File does not exist: {abs_path}")  # noqa: TRY301

                return True, abs_path
            except Exception:
                _LOGGER.exception(f"Failed to process file path '{content_str}'")
                raise

        # For strings, we need to determine if it's a file path or content
        if isinstance(content, str):
            # Criteria for being treated as a path:
            # 1. Starts with ./, /, \ or contains path separators
            # 2. AND doesn't contain any HTML-like tags
            # 3. AND doesn't look like CSS content (e.g., doesn't contain { or })
            is_likely_path = (
                (
                    content.strip().startswith(("./", "/", "\\"))
                    or (os.path.sep in content and not content.strip().startswith("."))
                )  # Avoid treating CSS classes as paths
                and "<" not in content
                and ">" not in content
                and "{" not in content
                and "}" not in content
            )

            if is_likely_path:
                try:
                    if os.path.isabs(content):
                        abs_path = content
                    else:
                        # Relative path, make it relative to the caller's file
                        caller_dir = os.path.dirname(_get_caller_path())
                        abs_path = os.path.abspath(os.path.join(caller_dir, content))

                    if not os.path.exists(abs_path):
                        raise ValueError(f"File does not exist: {abs_path}")  # noqa: TRY301

                    return True, abs_path
                except Exception:
                    _LOGGER.exception(f"Failed to process file path '{content}'")
                    raise

        # If we get here, it's content, not a path
        return False, None

    @property
    def css_url(self) -> str | None:
        """Return the URL to the CSS file if it's a path, otherwise None."""
        if not self._is_css_path:
            return None

        # If it's a path, get the filename
        if isinstance(self.css, Path):
            filename = self.css.name
        else:
            # It's a string path
            filename = os.path.basename(str(self.css))

        return f"{filename}"

    @property
    def js_url(self) -> str | None:
        """Return the URL to the JS file if it's a path, otherwise None."""
        if not self._is_js_path:
            return None

        # If it's a path, get the filename
        if isinstance(self.js, Path):
            filename = self.js.name
        else:
            # It's a string path
            filename = os.path.basename(str(self.js))

        return f"{filename}"

    @property
    def css_content(self) -> str | None:
        """Return the CSS content if it's inline content, otherwise None."""
        if self._is_css_path or self.css is None:
            return None
        # Return as string if it's not a path
        return str(self.css)

    @property
    def js_content(self) -> str | None:
        """Return the JS content if it's inline content, otherwise None."""
        if self._is_js_path or self.js is None:
            return None
        # Return as string if it's not a path
        return str(self.js)

    @property
    def html_content(self) -> str | None:
        """Return the HTML content."""
        return self.html

    @property
    def source_paths(self) -> dict[str, str]:
        """Return the source file directories for content loaded from files."""
        return self._source_paths


class BidiComponentRegistry:
    """Registry for bidirectional components V2."""

    def __init__(self):
        # TODO: Consider thread-safety implications more deeply if components
        # can be registered during runtime from different threads, though
        # typical usage might be mostly at import time. Using a lock for now.
        self._components: MutableMapping[str, BidiComponentDefinition] = {}
        self._lock = threading.Lock()

    def register(self, definition: BidiComponentDefinition) -> None:
        """Register a component definition.

        This method accepts either a BidiComponentDefinition object or
        the parameters to create one. If a component with the same name
        is already registered, it will be overwritten, and a warning is logged.

        For css and js parameters, the following formats are supported:
        - A string with the actual content
        - An absolute file path (string or Path)
        - A relative file path (string or Path, relative to the caller)

        Parameters
        ----------
        definition : BidiComponentDefinition
            A BidiComponentDefinition object.
        """

        # TODO: Handle the absolute path case

        # Register the definition
        with self._lock:
            name = definition.name
            if name in self._components:
                existing_definition = self._components[name]
                if existing_definition != definition:
                    _LOGGER.warning(
                        f"Component '{name}' is already registered. Overwriting "
                        "previous definition. This may lead to unexpected behavior "
                        "if different modules register the same component name with "
                        "different definitions."
                    )
            self._components[name] = definition
            _LOGGER.debug(f"Registered component '{name}'")

    def get(self, name: str) -> BidiComponentDefinition | None:
        """Get a component definition by name.

        Parameters
        ----------
        name : str
            The name of the component to retrieve.

        Returns
        -------
        BidiComponentDefinition or None
            The definition if found, otherwise None.
        """
        with self._lock:
            return self._components.get(name)

    def unregister(self, name: str) -> None:
        """Remove a component definition from the registry.

        Used primarily for testing or potential dynamic scenarios.

        Parameters
        ----------
        name : str
            The name of the component to unregister.
        """
        with self._lock:
            if name in self._components:
                del self._components[name]
                _LOGGER.debug(f"Unregistered component '{name}'")

    def clear(self) -> None:
        """Clear all component definitions from the registry."""
        with self._lock:
            self._components.clear()
            _LOGGER.debug("Cleared all components from registry")

    def get_component_path(self, name: str) -> str | None:
        """Return the filesystem path for the component with the given name.

        If no such component is registered, or if the component exists but doesn't
        have any content loaded from files, return None instead.

        Parameters
        ----------
        name : str
            The name of the component to retrieve the path for.

        Returns
        -------
        str or None
            The component's source directory if any content was loaded from files,
            otherwise None.
        """
        component = self.get(name)
        if component is None or not component.source_paths:
            return None

        # If we have multiple source paths, prefer js, then css
        for source_type in ["js", "css"]:
            if source_type in component.source_paths:
                return component.source_paths[source_type]

        return None
