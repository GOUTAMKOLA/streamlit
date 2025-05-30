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

from e2e_playwright.conftest import wait_for_app_run


def test_bidi_component_trigger_reset_on_other_widget_interaction(app: Page):
    """Test that bidi component trigger states reset when other widgets cause reruns."""

    # Wait for the app to load
    wait_for_app_run(app)

    # Verify initial state - clicked should be False
    expect(app.get_by_text("result.clicked: False 🔴")).to_be_visible()
    expect(app.get_by_text("Bidi click count: 0")).to_be_visible()
    expect(app.get_by_text("Button click count: 0")).to_be_visible()

    # Step 1: Click the bidi component's trigger button
    bidi_click_button = app.locator('button:has-text("Click Me (Trigger)")')
    expect(bidi_click_button).to_be_visible()
    bidi_click_button.click()

    wait_for_app_run(app)

    # Verify bidi component was clicked and callback was called
    expect(app.get_by_text("result.clicked: True 🟢")).to_be_visible()
    expect(app.get_by_text("Bidi click count: 1")).to_be_visible()
    expect(app.get_by_text("🎯 Bidi component was clicked! (Click #1)")).to_be_visible()

    # Step 2: Click the regular button - this should reset the bidi trigger
    regular_button = app.locator(
        'button:has-text("🔴 Regular Button (Click to trigger rerun)")'
    )
    expect(regular_button).to_be_visible()
    regular_button.click()

    wait_for_app_run(app)

    # Verify that:
    # 1. Regular button click was processed
    # 2. Bidi clicked state was reset to False
    # 3. Bidi click count did NOT increase (the bug we're fixing)
    expect(app.get_by_text("result.clicked: False 🔴")).to_be_visible()
    expect(app.get_by_text("Bidi click count: 1")).to_be_visible()  # Should stay at 1
    expect(app.get_by_text("Button click count: 1")).to_be_visible()
    expect(app.get_by_text("Regular button clicked! Click count: 1")).to_be_visible()


def test_bidi_component_trigger_reset_on_text_input(app: Page):
    """Test that bidi component trigger states reset when text input causes reruns."""

    # Wait for the app to load
    wait_for_app_run(app)

    # Click the bidi component first
    bidi_click_button = app.locator('button:has-text("Click Me (Trigger)")')
    bidi_click_button.click()
    wait_for_app_run(app)

    # Verify bidi component was clicked
    expect(app.get_by_text("result.clicked: True 🟢")).to_be_visible()
    expect(app.get_by_text("Bidi click count: 1")).to_be_visible()

    # Type in the text input - this should reset the bidi trigger
    text_input = app.locator('input[placeholder*="Type here"]')
    expect(text_input).to_be_visible()
    text_input.fill("test input")
    text_input.press("Enter")  # Trigger rerun

    wait_for_app_run(app)

    # Verify bidi trigger was reset and count didn't increase
    expect(app.get_by_text("result.clicked: False 🔴")).to_be_visible()
    expect(app.get_by_text("Bidi click count: 1")).to_be_visible()  # Should stay at 1


def test_bidi_component_trigger_reset_on_selectbox(app: Page):
    """Test that bidi component trigger states reset when selectbox causes reruns."""

    # Wait for the app to load
    wait_for_app_run(app)

    # Click the bidi component first
    bidi_click_button = app.locator('button:has-text("Click Me (Trigger)")')
    bidi_click_button.click()
    wait_for_app_run(app)

    # Verify bidi component was clicked
    expect(app.get_by_text("result.clicked: True 🟢")).to_be_visible()
    expect(app.get_by_text("Bidi click count: 1")).to_be_visible()

    # Change the selectbox - this should reset the bidi trigger
    selectbox = app.get_by_test_id("stSelectbox")
    selectbox.click()
    app.locator('li:has-text("Option 2")').click()

    wait_for_app_run(app)

    # Verify bidi trigger was reset and count didn't increase
    expect(app.get_by_text("result.clicked: False 🔴")).to_be_visible()
    expect(app.get_by_text("Bidi click count: 1")).to_be_visible()  # Should stay at 1


def test_bidi_component_form_submission_preserves_persistent_value(app: Page):
    """Test that submitting the bidi component form updates persistent value but doesn't trigger click."""

    # Wait for the app to load
    wait_for_app_run(app)

    # Verify initial state
    expect(app.get_by_text("result.value: None")).to_be_visible()
    expect(app.get_by_text("result.clicked: False 🔴")).to_be_visible()
    expect(app.get_by_text("Bidi click count: 0")).to_be_visible()

    # Modify the text input in the bidi component and submit the form
    bidi_text_input = app.locator('input[value="Hello"]')
    expect(bidi_text_input).to_be_visible()
    bidi_text_input.fill("Updated text")

    # Submit the form (green button)
    submit_button = app.locator('button:has-text("Submit Form (Persistent)")')
    expect(submit_button).to_be_visible()
    submit_button.click()

    wait_for_app_run(app)

    # Verify form submission was processed but clicked remains False
    expect(app.get_by_text("📝 Bidi component form was submitted!")).to_be_visible()
    expect(app.get_by_text("result.clicked: False 🔴")).to_be_visible()
    expect(app.get_by_text("Bidi click count: 0")).to_be_visible()  # Should stay at 0


def test_bidi_component_multiple_click_cycles(app: Page):
    """Test multiple cycles of clicking bidi component and other widgets."""

    # Wait for the app to load
    wait_for_app_run(app)

    # Cycle 1: Click bidi, then regular button
    bidi_click_button = app.locator('button:has-text("Click Me (Trigger)")')
    regular_button = app.locator(
        'button:has-text("🔴 Regular Button (Click to trigger rerun)")'
    )

    # Click bidi component
    bidi_click_button.click()
    wait_for_app_run(app)
    expect(app.get_by_text("result.clicked: True 🟢")).to_be_visible()
    expect(app.get_by_text("Bidi click count: 1")).to_be_visible()

    # Click regular button
    regular_button.click()
    wait_for_app_run(app)
    expect(app.get_by_text("result.clicked: False 🔴")).to_be_visible()
    expect(app.get_by_text("Bidi click count: 1")).to_be_visible()
    expect(app.get_by_text("Button click count: 1")).to_be_visible()

    # Cycle 2: Click bidi again, then regular button again
    bidi_click_button.click()
    wait_for_app_run(app)
    expect(app.get_by_text("result.clicked: True 🟢")).to_be_visible()
    expect(app.get_by_text("Bidi click count: 2")).to_be_visible()

    regular_button.click()
    wait_for_app_run(app)
    expect(app.get_by_text("result.clicked: False 🔴")).to_be_visible()
    expect(app.get_by_text("Bidi click count: 2")).to_be_visible()  # Should stay at 2
    expect(app.get_by_text("Button click count: 2")).to_be_visible()


def test_bidi_component_trigger_only_called_on_actual_trigger(app: Page):
    """Test that bidi component trigger callback is only called when actually triggered."""

    # Wait for the app to load
    wait_for_app_run(app)

    # Initial state - no callbacks should have been called
    expect(app.get_by_text("Bidi click count: 0")).to_be_visible()

    # Click regular button first - this should NOT trigger bidi callback
    regular_button = app.locator(
        'button:has-text("🔴 Regular Button (Click to trigger rerun)")'
    )
    regular_button.click()
    wait_for_app_run(app)

    # Verify bidi callback was NOT called
    expect(app.get_by_text("Bidi click count: 0")).to_be_visible()
    expect(app.get_by_text("Button click count: 1")).to_be_visible()

    # Type in text input - this should also NOT trigger bidi callback
    text_input = app.locator('input[placeholder*="Type here"]')
    text_input.fill("some text")
    text_input.press("Enter")
    wait_for_app_run(app)

    # Verify bidi callback still was NOT called
    expect(app.get_by_text("Bidi click count: `0`")).to_be_visible()

    # Now actually click the bidi component - this SHOULD trigger the callback
    bidi_click_button = app.locator('button:has-text("Click Me (Trigger)")')
    bidi_click_button.click()
    wait_for_app_run(app)

    # Verify bidi callback was called exactly once
    expect(app.get_by_text("Bidi click count: 1")).to_be_visible()
    expect(app.get_by_text("🎯 Bidi component was clicked! (Click #1)")).to_be_visible()
