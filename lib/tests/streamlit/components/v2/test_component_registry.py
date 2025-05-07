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

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.components.v2.component_registry import (
    BidiComponentDefinition,
    BidiComponentRegistry,
)


class BidiComponentDefinitionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()

        # Create test files
        self.js_path = os.path.join(self.temp_dir.name, "index.js")
        with open(self.js_path, "w") as f:
            f.write("console.log('test');")

        self.html_path = os.path.join(self.temp_dir.name, "index.html")
        with open(self.html_path, "w") as f:
            f.write("<div>Test</div>")

        self.css_path = os.path.join(self.temp_dir.name, "styles.css")
        with open(self.css_path, "w") as f:
            f.write("div { color: blue; }")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_string_content(self) -> None:
        """Test component with direct string content."""
        comp = BidiComponentDefinition(
            name="test",
            html="<div>Hello</div>",
            css=".div { color: red; }",
            js="console.log('hello');",
        )

        self.assertEqual(comp.html_content, "<div>Hello</div>")
        self.assertEqual(comp.css_content, ".div { color: red; }")
        self.assertEqual(comp.js_content, "console.log('hello');")
        self.assertIsNone(comp.css_url)
        self.assertIsNone(comp.js_url)
        self.assertEqual(comp.source_paths, {})

    def test_file_path_content(self) -> None:
        """Test component with file path content."""
        with patch(
            "streamlit.components.v2.component_registry._get_caller_path"
        ) as mock_caller:
            # Mock the caller path to be the temp directory
            mock_caller.return_value = os.path.join(self.temp_dir.name, "caller.py")

            comp = BidiComponentDefinition(
                name="test",
                js=self.js_path,
                html="<div>Inline HTML</div>",  # HTML should be a string, not a path
                css=self.css_path,
            )

            self.assertEqual(comp.html_content, "<div>Inline HTML</div>")
            self.assertIsNone(
                comp.css_content
            )  # CSS content is None because it's a path
            self.assertIsNone(comp.js_content)  # JS content is None because it's a path

            # Check URLs are generated for path resources
            self.assertEqual(
                comp.css_url, f"bidi_components/test/{os.path.basename(self.css_path)}"
            )
            self.assertEqual(
                comp.js_url, f"bidi_components/test/{os.path.basename(self.js_path)}"
            )

            # Check source paths
            self.assertEqual(len(comp.source_paths), 2)
            self.assertEqual(comp.source_paths["css"], os.path.dirname(self.css_path))
            self.assertEqual(comp.source_paths["js"], os.path.dirname(self.js_path))
            self.assertNotIn("html", comp.source_paths)

    def test_mixed_content(self) -> None:
        """Test component with mixed string and file content."""
        with patch(
            "streamlit.components.v2.component_registry._get_caller_path"
        ) as mock_caller:
            # Mock the caller path to be the temp directory
            mock_caller.return_value = os.path.join(self.temp_dir.name, "caller.py")

            comp = BidiComponentDefinition(
                name="test",
                js=self.js_path,  # File path
                html="<div>Inline HTML</div>",  # String
                css="div { color: green; }",  # String
            )

            self.assertEqual(comp.html_content, "<div>Inline HTML</div>")
            self.assertEqual(comp.css_content, "div { color: green; }")
            self.assertIsNone(comp.js_content)  # JS content is None because it's a path

            # Check URLs
            self.assertIsNone(comp.css_url)  # No URL for inline CSS
            self.assertEqual(
                comp.js_url, f"bidi_components/test/{os.path.basename(self.js_path)}"
            )

            # Only JS should have a source path
            self.assertEqual(len(comp.source_paths), 1)
            self.assertEqual(comp.source_paths["js"], os.path.dirname(self.js_path))

    def test_pathlib_path(self) -> None:
        """Test component with Path object."""
        with patch(
            "streamlit.components.v2.component_registry._get_caller_path"
        ) as mock_caller:
            # Mock the caller path to be the temp directory
            mock_caller.return_value = os.path.join(self.temp_dir.name, "caller.py")

            js_pathlib = Path(self.js_path)

            comp = BidiComponentDefinition(
                name="test",
                js=js_pathlib,
            )

            self.assertIsNone(comp.js_content)  # JS content is None because it's a path
            self.assertEqual(comp.js_url, f"bidi_components/test/{js_pathlib.name}")
            self.assertEqual(comp.source_paths["js"], os.path.dirname(self.js_path))


class BidiComponentRegistryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry = BidiComponentRegistry()

        # Create test files
        self.js_path = os.path.join(self.temp_dir.name, "index.js")
        with open(self.js_path, "w") as f:
            f.write("console.log('test');")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_get_component_path_with_file_path(self) -> None:
        """Test get_component_path with a component using file paths."""
        with patch(
            "streamlit.components.v2.component_registry._get_caller_path"
        ) as mock_caller:
            mock_caller.return_value = os.path.join(self.temp_dir.name, "caller.py")

            self.registry.register(
                BidiComponentDefinition(
                    name="test_component",
                    js=self.js_path,
                )
            )

            path = self.registry.get_component_path("test_component")
            self.assertEqual(path, os.path.dirname(self.js_path))

    def test_get_component_path_with_string_content(self) -> None:
        """Test get_component_path with a component using string content."""
        self.registry.register(
            BidiComponentDefinition(
                name="string_component",
                js="console.log('string content');",
            )
        )

        path = self.registry.get_component_path("string_component")
        self.assertIsNone(path)

    def test_get_component_path_nonexistent_component(self) -> None:
        """Test get_component_path with a nonexistent component."""
        path = self.registry.get_component_path("nonexistent")
        self.assertIsNone(path)


if __name__ == "__main__":
    unittest.main()
