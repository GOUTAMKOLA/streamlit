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


def test_trigger_interactions(app: Page):
    """Test the interactions with trigger callbacks and state in the Bidi Component."""
    expect(app.get_by_text("Foo count: 0")).to_be_visible()
    expect(app.get_by_text("Bar count: 0")).to_be_visible()
    expect(
        app.get_by_text(
            "Result: {'delta_generator': DeltaGenerator(), 'foo': None, 'bar': None}"
        )
    ).to_be_visible()

    app.get_by_text("Trigger foo").click()
    expect(app.get_by_text("Foo count: 1")).to_be_visible()
    expect(app.get_by_text("Bar count: 0")).to_be_visible()
    expect(
        app.get_by_text(
            "Result: {'delta_generator': DeltaGenerator(), 'foo': True, 'bar': None}"
        )
    ).to_be_visible()

    app.get_by_text("Trigger bar").click()
    expect(app.get_by_text("Foo count: 1")).to_be_visible()
    expect(app.get_by_text("Bar count: 1")).to_be_visible()
    expect(
        app.get_by_text(
            "Result: {'delta_generator': DeltaGenerator(), 'foo': None, 'bar': True}"
        )
    ).to_be_visible()

    # Trigger foo again so it has a different value from bar
    app.get_by_text("Trigger foo").click()
    expect(app.get_by_text("Foo count: 2")).to_be_visible()
    expect(app.get_by_text("Bar count: 1")).to_be_visible()
    expect(
        app.get_by_text(
            "Result: {'delta_generator': DeltaGenerator(), 'foo': True, 'bar': None}"
        )
    ).to_be_visible()

    app.get_by_text("Trigger both").click()
    expect(app.get_by_text("Foo count: 3")).to_be_visible()
    expect(app.get_by_text("Bar count: 2")).to_be_visible()
    expect(
        app.get_by_text(
            "Result: {'delta_generator': DeltaGenerator(), 'foo': True, 'bar': True}"
        )
    ).to_be_visible()

    # Trigger a streamlit button to ensure the trigger values in the Bidi
    # Component get reset
    app.get_by_text("st.button trigger").click()
    expect(app.get_by_text("Foo count: 3")).to_be_visible()
    expect(app.get_by_text("Bar count: 2")).to_be_visible()
    expect(
        app.get_by_text(
            "Result: {'delta_generator': DeltaGenerator(), 'foo': None, 'bar': None}"
        )
    ).to_be_visible()
