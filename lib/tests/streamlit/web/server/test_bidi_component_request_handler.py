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

import tornado.testing
import tornado.web

from streamlit.components.v2.component_registry import (
    BidiComponentDefinition,
    BidiComponentRegistry,
)
from streamlit.web.server.bidi_component_request_handler import (
    BidiComponentRequestHandler,
)


class BidiComponentRequestHandlerTest(tornado.testing.AsyncHTTPTestCase):
    def setUp(self) -> None:
        self.registry = BidiComponentRegistry()
        self.temp_dir = tempfile.TemporaryDirectory()
        super().setUp()

        # Create a sample component directory for testing
        self.component_path = os.path.join(self.temp_dir.name, "test_component")
        os.makedirs(self.component_path, exist_ok=True)

        # Create a JS file
        self.js_path = os.path.join(self.component_path, "index.js")
        with open(self.js_path, "w") as f:
            f.write("console.log('test component');")

        # Create an HTML file
        self.html_path = os.path.join(self.component_path, "index.html")
        with open(self.html_path, "w") as f:
            f.write("<div>Test Component</div>")

        # Create a CSS file
        self.css_path = os.path.join(self.component_path, "styles.css")
        with open(self.css_path, "w") as f:
            f.write("div { color: red; }")

        # Register a test component using the JS file path
        self.registry.register(
            BidiComponentDefinition(
                name="test_component",
                js=self.js_path,
            )
        )

        # Register a component with HTML content (not a file path)
        self.registry.register(
            BidiComponentDefinition(
                name="html_component",
                html="<div>Test Component</div>",
            )
        )

    def tearDown(self) -> None:
        super().tearDown()
        self.temp_dir.cleanup()

    def get_app(self) -> tornado.web.Application:
        return tornado.web.Application(
            [
                (
                    r"/bidi_components/(.*)",
                    BidiComponentRequestHandler,
                    {"registry": self.registry},
                )
            ]
        )

    def test_get_component_file(self) -> None:
        response = self.fetch("/bidi_components/test_component/index.js")
        assert response.code == 200
        assert response.body.decode() == "console.log('test component');"

    def test_component_not_found(self) -> None:
        response = self.fetch("/bidi_components/nonexistent_component/index.js")
        assert response.code == 404

    def test_component_path_not_found(self) -> None:
        # Register a component without any file paths
        self.registry.register(
            BidiComponentDefinition(
                name="no_path_component",
                js="console.log('no path');",
            )
        )
        response = self.fetch("/bidi_components/no_path_component/index.js")
        assert response.code == 404

    def test_multiple_file_components(self) -> None:
        """Test component with multiple file references."""
        # Create a component with multiple file sources (but HTML as string)
        self.registry.register(
            BidiComponentDefinition(
                name="multi_file_component",
                js=self.js_path,
                html="<div>Test Component</div>",  # HTML as string
                css=self.css_path,
            )
        )

        # JS should be accessible
        response = self.fetch("/bidi_components/multi_file_component/index.js")
        assert response.code == 200
        assert response.body.decode() == "console.log('test component');"

        # HTML files should NOT be accessible through the file handler
        # since HTML is only accepted as a string
        response = self.fetch("/bidi_components/multi_file_component/index.html")
        assert response.code == 404

        # CSS should be accessible
        response = self.fetch("/bidi_components/multi_file_component/styles.css")
        assert response.code == 200
        assert response.body.decode() == "div { color: red; }"

    def test_disallow_path_traversal(self) -> None:
        # Attempt path traversal attack
        response = self.fetch("/bidi_components/test_component/../../../etc/passwd")
        assert response.code == 403

    def test_file_not_found_in_component_dir(self) -> None:
        response = self.fetch("/bidi_components/test_component/nonexistent.js")
        assert response.code == 404

    def test_get_url(self) -> None:
        url = BidiComponentRequestHandler.get_url("test_component/index.js")
        assert url == "bidi_components/test_component/index.js"


if __name__ == "__main__":
    unittest.main()
