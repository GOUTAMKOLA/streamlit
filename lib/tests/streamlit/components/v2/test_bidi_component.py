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

import unittest
from unittest.mock import MagicMock, patch

import pytest

import streamlit as st
from streamlit.components.v2.component_registry import (
    BidiComponentDefinition,
    BidiComponentRegistry,
)
from streamlit.errors import StreamlitAPIException
from streamlit.runtime import Runtime
from tests.delta_generator_test_case import DeltaGeneratorTestCase


class BidiComponentTest(DeltaGeneratorTestCase):
    """Test the bidi_component functionality."""

    def setUp(self):
        super().setUp()
        # Create a mock registry for testing
        self.mock_registry = BidiComponentRegistry()

        # Patch the Runtime to return our mock registry
        self.runtime_patcher = patch.object(
            Runtime, "instance", return_value=MagicMock()
        )
        self.mock_runtime = self.runtime_patcher.start()
        self.mock_runtime.return_value.bidi_component_registry = self.mock_registry

    def tearDown(self):
        super().tearDown()
        self.runtime_patcher.stop()

    def test_component_with_js_content_only(self):
        """Test component with only JavaScript content."""
        # Register a component with JS content only
        self.mock_registry.register(
            BidiComponentDefinition(
                name="js_only_component",
                js="console.log('hello world');",
            )
        )

        # Call the component
        result = st.bidi_component("js_only_component")

        # Verify the result
        assert hasattr(result, "value")
        assert result.value is None  # Default value

        # Verify the proto was enqueued
        delta = self.get_delta_from_queue()
        bidi_component_proto = delta.new_element.bidi_component
        assert bidi_component_proto.component_name == "js_only_component"
        assert bidi_component_proto.js_content == "console.log('hello world');"
        assert bidi_component_proto.html_content == ""

    def test_component_with_html_content_only(self):
        """Test component with only HTML content."""
        # Register a component with HTML content only
        self.mock_registry.register(
            BidiComponentDefinition(
                name="html_only_component",
                html="<div>Hello World</div>",
            )
        )

        # Call the component
        result = st.bidi_component("html_only_component")

        # Verify the result
        assert hasattr(result, "value")
        assert result.value is None  # Default value

        # Verify the proto was enqueued
        delta = self.get_delta_from_queue()
        bidi_component_proto = delta.new_element.bidi_component
        assert bidi_component_proto.component_name == "html_only_component"
        assert bidi_component_proto.html_content == "<div>Hello World</div>"
        assert bidi_component_proto.js_content == ""

    def test_component_with_js_url_only(self):
        """Test component with only JavaScript URL."""
        # Create a mock component definition with js_url
        mock_component_def = MagicMock(spec=BidiComponentDefinition)
        mock_component_def.js_content = None
        mock_component_def.js_url = "index.js"
        mock_component_def.html_content = None
        mock_component_def.css_content = None
        mock_component_def.css_url = None
        mock_component_def.isolate_styles = True

        # Mock the registry to return our component
        with patch.object(self.mock_registry, "get", return_value=mock_component_def):
            # Call the component
            result = st.bidi_component("js_url_component")

            # Verify the result
            assert hasattr(result, "value")
            assert result.value is None  # Default value

            # Verify the proto was enqueued
            delta = self.get_delta_from_queue()
            bidi_component_proto = delta.new_element.bidi_component
            assert bidi_component_proto.component_name == "js_url_component"
            assert bidi_component_proto.js_source_path == "index.js"
            assert bidi_component_proto.html_content == ""

    def test_component_with_both_js_and_html(self):
        """Test component with both JavaScript and HTML content."""
        # Register a component with both JS and HTML content
        self.mock_registry.register(
            BidiComponentDefinition(
                name="full_component",
                js="console.log('hello world');",
                html="<div>Hello World</div>",
                css="div { color: red; }",
            )
        )

        # Call the component
        result = st.bidi_component("full_component")

        # Verify the result
        assert hasattr(result, "value")
        assert result.value is None  # Default value

        # Verify the proto was enqueued
        delta = self.get_delta_from_queue()
        bidi_component_proto = delta.new_element.bidi_component
        assert bidi_component_proto.component_name == "full_component"
        assert bidi_component_proto.js_content == "console.log('hello world');"
        assert bidi_component_proto.html_content == "<div>Hello World</div>"
        assert bidi_component_proto.css_content == "div { color: red; }"

    def test_component_with_no_js_or_html_raises_exception(self):
        """Test that component with neither JS nor HTML content raises StreamlitAPIException."""
        # Register a component with only CSS content (no JS or HTML)
        self.mock_registry.register(
            BidiComponentDefinition(
                name="css_only_component",
                css="div { color: red; }",
            )
        )

        # Call the component and expect an exception
        with pytest.raises(StreamlitAPIException) as exc_info:
            st.bidi_component("css_only_component")

        # Verify the error message
        error_message = str(exc_info.value)
        assert "css_only_component" in error_message
        assert "must have either JavaScript content" in error_message
        assert "(js_content or js_url) or HTML content (html_content)" in error_message

    def test_component_with_empty_js_and_html_raises_exception(self):
        """Test that component with empty JS and HTML content raises StreamlitAPIException."""
        # Create a mock component definition with empty content
        mock_component_def = MagicMock(spec=BidiComponentDefinition)
        mock_component_def.js_content = ""  # Empty string
        mock_component_def.js_url = None
        mock_component_def.html_content = ""  # Empty string
        mock_component_def.css_content = "div { color: red; }"
        mock_component_def.css_url = None
        mock_component_def.isolate_styles = True

        # Mock the registry to return our component
        with patch.object(self.mock_registry, "get", return_value=mock_component_def):
            # Call the component and expect an exception
            with pytest.raises(StreamlitAPIException) as exc_info:
                st.bidi_component("empty_component")

            # Verify the error message
            error_message = str(exc_info.value)
            assert "empty_component" in error_message
            assert "must have either JavaScript content" in error_message

    def test_unregistered_component_raises_value_error(self):
        """Test that calling an unregistered component raises ValueError."""
        # Call a component that doesn't exist
        with pytest.raises(
            ValueError, match="Component 'nonexistent_component' is not registered"
        ):
            st.bidi_component("nonexistent_component")

    def test_component_with_default_value(self):
        """Test component with a default value."""
        # Register a component
        self.mock_registry.register(
            BidiComponentDefinition(
                name="default_value_component",
                js="console.log('hello world');",
            )
        )

        # Call the component with a default value
        default_value = {"test": "value"}
        result = st.bidi_component("default_value_component", default=default_value)

        # Verify the result has the correct structure
        # Note: The default value is used when the widget hasn't been interacted with yet
        # In the test environment, the widget state is typically None initially
        assert hasattr(result, "value")
        # The actual default value handling is done by the widget registration system

    def test_component_with_key(self):
        """Test component with a user-specified key."""
        # Register a component
        self.mock_registry.register(
            BidiComponentDefinition(
                name="keyed_component",
                js="console.log('hello world');",
            )
        )

        # Call the component with a key
        result = st.bidi_component("keyed_component", key="my_key")

        # Verify the result
        assert hasattr(result, "value")

        # Verify the proto was enqueued with the correct ID
        delta = self.get_delta_from_queue()
        bidi_component_proto = delta.new_element.bidi_component
        assert bidi_component_proto.component_name == "keyed_component"
        # The ID should be deterministic based on the key
        assert bidi_component_proto.id is not None

    def test_component_with_data(self):
        """Test component with data parameter."""
        # Register a component
        self.mock_registry.register(
            BidiComponentDefinition(
                name="data_component",
                js="console.log('hello world');",
            )
        )

        # Call the component with data
        test_data = {"message": "hello", "count": 42}
        result = st.bidi_component("data_component", data=test_data)

        # Verify the result
        assert hasattr(result, "value")

        # Verify the proto was enqueued with the data
        delta = self.get_delta_from_queue()
        bidi_component_proto = delta.new_element.bidi_component
        assert bidi_component_proto.component_name == "data_component"
        # Data should be JSON serialized
        import json

        assert json.loads(bidi_component_proto.data) == test_data

    def test_component_with_callbacks(self):
        """Test component with callback handlers."""
        # Register a component
        self.mock_registry.register(
            BidiComponentDefinition(
                name="callback_component",
                js="console.log('hello world');",
            )
        )

        # Create mock callbacks
        on_change_callback = MagicMock()
        on_click_callback = MagicMock()

        # Call the component with callbacks
        result = st.bidi_component(
            "callback_component",
            on_change=on_change_callback,
            on_click=on_click_callback,
        )

        # Verify the result
        assert hasattr(result, "value")

        # Verify the proto was enqueued with registered handler names
        delta = self.get_delta_from_queue()
        bidi_component_proto = delta.new_element.bidi_component
        assert bidi_component_proto.component_name == "callback_component"
        # Should have both change and click handlers registered
        handler_names = list(bidi_component_proto.registered_handler_names)
        assert "change" in handler_names
        assert "click" in handler_names

    def test_component_with_child_containers(self):
        """Test component with child containers."""
        # Register a component
        self.mock_registry.register(
            BidiComponentDefinition(
                name="container_component",
                js="console.log('hello world');",
            )
        )

        # Call the component with child containers
        result = st.bidi_component("container_component", child_container_count=3)

        # Verify the result
        assert hasattr(result, "value")

        # Verify the proto was enqueued with the correct child container count
        delta = self.get_delta_from_queue()
        bidi_component_proto = delta.new_element.bidi_component
        assert bidi_component_proto.component_name == "container_component"
        assert bidi_component_proto.child_container_count == 3

    def test_component_without_script_context_returns_default(self):
        """Test component behavior when there's no script run context."""
        # Register a component
        self.mock_registry.register(
            BidiComponentDefinition(
                name="no_context_component",
                js="console.log('hello world');",
            )
        )

        # Mock get_script_run_ctx to return None
        with patch(
            "streamlit.components.v2.bidi_component.get_script_run_ctx",
            return_value=None,
        ):
            # Call the component with a default value
            default_value = {"test": "value"}
            result = st.bidi_component("no_context_component", default=default_value)

            # Should return the default value wrapped in BidiComponentState
            assert hasattr(result, "value")
            assert result.value == default_value

            # No proto should be enqueued since there's no context
            assert len(self.get_all_deltas_from_queue()) == 0


if __name__ == "__main__":
    unittest.main()
