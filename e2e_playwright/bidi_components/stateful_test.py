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

from playwright.sync_api import Page, expect


def test_stateful_interactions(app: Page):
    expect(app.get_by_label("Range")).to_have_value("50")
    expect(app.get_by_label("Text")).to_have_value("Text input")

    expect(
        app.get_by_text(
            "Result: {'delta_generator': DeltaGenerator(), 'range': None, 'text': None}"
        )
    ).to_be_visible()

    expect(app.get_by_text("Range change count: 0")).to_be_visible()
    expect(app.get_by_text("Text change count: 0")).to_be_visible()

    # Change Range value
    app.get_by_label("Range").fill("10")
    # Assert that only Range has changed, because they are 2 independent pieces
    # of state
    expect(app.get_by_label("Range")).to_have_value("10")
    expect(
        app.get_by_text(
            "Result: {'delta_generator': DeltaGenerator(), 'range': '10', 'text': None}"
        )
    ).to_be_visible()
    expect(app.get_by_text("Range change count: 1")).to_be_visible()
    expect(app.get_by_text("Text change count: 0")).to_be_visible()

    # Change Text value
    app.get_by_label("Text").fill("Hello")
    # Assert that only Text has changed, because they are 2 independent pieces
    # of state
    expect(app.get_by_label("Text")).to_have_value("Hello")
    expect(
        app.get_by_text(
            "Result: {'delta_generator': DeltaGenerator(), 'range': '10', 'text': 'Hello'}"
        )
    ).to_be_visible()

    expect(app.get_by_text("Range change count: 1")).to_be_visible()
    expect(app.get_by_text("Text change count: 1")).to_be_visible()

    # Trigger a streamlit button to ensure the values are not reset
    app.get_by_text("st.button trigger").click()
    expect(
        app.get_by_text(
            "Result: {'delta_generator': DeltaGenerator(), 'range': '10', 'text': 'Hello'}"
        )
    ).to_be_visible()
    expect(app.get_by_text("Range change count: 1")).to_be_visible()
    expect(app.get_by_text("Text change count: 1")).to_be_visible()
