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

"""Tests for BidiComponentRegistry initialization within AppSession."""

import unittest
from unittest.mock import MagicMock, patch

from streamlit.components.v2.component_registry import (
    BidiComponentRegistry,
)
from streamlit.runtime.app_session import AppSession  # Added
from streamlit.runtime.runtime import Runtime  # Keep for tearDown
from streamlit.runtime.script_data import ScriptData  # Added


class AppSessionBidiComponentRegistryTest(unittest.TestCase):  # Renamed class
    """Test that AppSession correctly initializes its BidiComponentRegistry."""  # Updated docstring

    def tearDown(self) -> None:
        # Clear the singleton instance after each test
        # This might be relevant if other tests in a larger suite interact with Runtime
        if hasattr(Runtime, "_instance"):
            Runtime._instance = None

    def test_appsession_initializes_bidi_component_registry(self):
        """Test that AppSession initializes a BidiComponentRegistry instance."""
        mock_script_data = ScriptData("test_path.py", False)
        mock_uploaded_file_manager = MagicMock()
        mock_script_cache = MagicMock()
        mock_message_enqueued_callback = MagicMock()
        mock_user_info: dict[str, str | bool | None] = {"email": "test@example.com"}

        # AppSession.__init__ calls asyncio.get_running_loop()
        with patch("asyncio.get_running_loop", MagicMock()):
            app_session = AppSession(
                script_data=mock_script_data,
                uploaded_file_manager=mock_uploaded_file_manager,
                script_cache=mock_script_cache,
                message_enqueued_callback=mock_message_enqueued_callback,
                user_info=mock_user_info,
            )

        self.assertIsNotNone(app_session.bidi_component_registry)
        self.assertIsInstance(
            app_session.bidi_component_registry, BidiComponentRegistry
        )

    # The following test is removed as custom registry injection via RuntimeConfig is no longer possible.
    # @patch("streamlit.runtime.runtime.MediaFileManager", autospec=True)
    # def test_custom_bidi_component_registry(self, mock_media_file_manager):
    #     """Test that a custom BidiComponentRegistry can be provided to the runtime."""
    #     # Create a custom registry
    #     custom_registry = BidiComponentRegistry()
    #     custom_registry.register(
    #         BidiComponentDefinition(
    #             name="test_component",
    #             html="<div>Test</div>",
    #         )
    #     )
    #     # Create a mock config with our custom registry
    #     config = RuntimeConfig(
    #         script_path="test_path",
    #         command_line=None,
    #         media_file_storage=MagicMock(),
    #         uploaded_file_manager=MagicMock(),
    #         bidi_component_registry=custom_registry,
    #     )
    #     # Initialize the runtime
    #     runtime = Runtime(config)
    #     # Verify that our custom registry is used
    #     self.assertIs(runtime.bidi_component_registry, custom_registry)
    #     self.assertIsNotNone(runtime.bidi_component_registry.get("test_component"))
