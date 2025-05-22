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

"""Tests for the BidiComponentRegistry in the Runtime."""

import unittest
from unittest.mock import MagicMock, patch

from streamlit.components.v2.component_registry import (
    BidiComponentDefinition,
    BidiComponentRegistry,
)
from streamlit.runtime.runtime import Runtime, RuntimeConfig


class BidiComponentRegistryTest(unittest.TestCase):
    """Test that the BidiComponentRegistry is properly initialized in the runtime."""

    def tearDown(self) -> None:
        # Clear the singleton instance after each test
        Runtime._instance = None

    @patch("streamlit.runtime.runtime.MediaFileManager", autospec=True)
    def test_bidi_component_registry_initialization(self, mock_media_file_manager):
        """Test that the BidiComponentRegistry is properly initialized."""
        # Create a mock config with minimum required parameters
        config = RuntimeConfig(
            script_path="test_path",
            command_line=None,
            media_file_storage=MagicMock(),
            uploaded_file_manager=MagicMock(),
        )

        # Initialize the runtime
        runtime = Runtime(config)

        # Verify that the BidiComponentRegistry is initialized
        assert runtime.bidi_component_registry is not None
        assert isinstance(runtime.bidi_component_registry, BidiComponentRegistry)

    @patch("streamlit.runtime.runtime.MediaFileManager", autospec=True)
    def test_custom_bidi_component_registry(self, mock_media_file_manager):
        """Test that a custom BidiComponentRegistry can be provided to the runtime."""
        # Create a custom registry
        custom_registry = BidiComponentRegistry()
        custom_registry.register(
            BidiComponentDefinition(
                name="test_component",
                html="<div>Test</div>",
            )
        )

        # Create a mock config with our custom registry
        config = RuntimeConfig(
            script_path="test_path",
            command_line=None,
            media_file_storage=MagicMock(),
            uploaded_file_manager=MagicMock(),
            bidi_component_registry=custom_registry,
        )

        # Initialize the runtime
        runtime = Runtime(config)

        # Verify that our custom registry is used
        assert runtime.bidi_component_registry is custom_registry
        assert runtime.bidi_component_registry.get("test_component") is not None
