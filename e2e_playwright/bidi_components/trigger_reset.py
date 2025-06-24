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


import streamlit as st
from streamlit.components.v2.bidi_component import BidiComponentResult

st.header("Bidi Component Trigger Reset Test")

st.write("""
This app tests whether bidi component trigger states (like `clicked`) properly reset
when OTHER widgets cause a rerun. This is critical behavior for trigger widgets.

**Expected behavior:**
1. Click the bidi component → `clicked` should become `True`
2. Click the regular button → this should cause a rerun and `clicked` should reset to `False`
3. Interact with text input → this should also reset `clicked` to `False`
""")

# Initialize session state for tracking
if "button_clicks" not in st.session_state:
    st.session_state.button_clicks = 0
if "last_bidi_clicked" not in st.session_state:
    st.session_state.last_bidi_clicked = False
if "bidi_click_count" not in st.session_state:
    st.session_state.bidi_click_count = 0


def my_bidi_component() -> BidiComponentResult:
    """A simple bidi component that supports both change and click events."""

    js_code = """
export default function(component) {
  console.log("Bidi component initialized", component)

  const { parentElement, onChange, onClick } = component

  // Create the component HTML
  const form = document.createElement('form')
  form.innerHTML = `
    <div style="border: 2px solid #1f77b4; padding: 20px; border-radius: 8px; background: #f0f8ff;">
      <h3>Bidi Component</h3>
      <label for="text-input">Text Input:</label>
      <input type="text" id="text-input" value="Hello" style="margin: 10px; padding: 5px;" />
      <br/>
      <button type="button" id="click-btn" style="
        margin: 10px; padding: 10px 20px; background: #1f77b4; color: white; border: none; border-radius: 4px;
      ">
        Click Me (Trigger)
      </button>
      <button type="submit" style="
        margin: 10px; padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 4px;
      ">
        Submit Form (Persistent)
      </button>
    </div>
  `

  parentElement.appendChild(form)

  // Handle form submission (persistent change)
  const handleSubmit = (event) => {
    event.preventDefault()
    const textValue = event.target.querySelector('#text-input').value
    console.log("Form submitted with value:", textValue)
    onChange({ text: textValue })
  }

  // Handle click button (trigger)
  const handleClick = () => {
    console.log("Click button pressed")
    onClick()
  }

  form.addEventListener('submit', handleSubmit)
  form.querySelector('#click-btn').addEventListener('click', handleClick)

  return () => {
    console.log("Cleaning up bidi component")
    form.removeEventListener('submit', handleSubmit)
    form.querySelector('#click-btn').removeEventListener('click', handleClick)
  }
}
"""

    def handle_bidi_click():
        st.session_state.bidi_click_count += 1
        st.write(
            f"🎯 Bidi component was clicked! (Click #{st.session_state.bidi_click_count})"
        )

    def handle_bidi_change():
        st.write("📝 Bidi component form was submitted!")

    result = st.components.v2.component(
        name="trigger_reset_test_component",
        js=js_code,
        html="",  # HTML is created in JS
        key="bidi_test",
        on_change=handle_bidi_change,
        on_click=handle_bidi_click,
    )

    return result


# Create the bidi component
bidi_result = my_bidi_component()

# Track the clicked state
current_clicked = bidi_result.clicked if hasattr(bidi_result, "clicked") else False
st.session_state.last_bidi_clicked = current_clicked

# Display current state
st.write("## Current State:")
col1, col2 = st.columns(2)

with col1:
    st.write("**Bidi Component State:**")
    st.write(f"- result.value: {bidi_result.value}")
    st.write(f"- result.clicked: {current_clicked} {'🟢' if current_clicked else '🔴'}")

with col2:
    st.write("**Session State:**")
    st.write(f"- Bidi click count: {st.session_state.bidi_click_count}")
    st.write(f"- Button click count: {st.session_state.button_clicks}")

st.write("---")

# Other widgets that should cause trigger reset
st.write("## Other Widgets (These should reset bidi `clicked` to False):")

# Regular button
if st.button("🔴 Regular Button (Click to trigger rerun)"):
    st.session_state.button_clicks += 1
    st.write(f"Regular button clicked! Click count: {st.session_state.button_clicks}")

# Text input
text_value = st.text_input("✏️ Text Input (Type to trigger rerun)", value="Type here...")

# Selectbox
option = st.selectbox(
    "📋 Selectbox (Change to trigger rerun)", ["Option 1", "Option 2", "Option 3"]
)

st.write("---")

# Instructions and diagnostics
st.write("## Test Instructions:")
st.write("""
1. **Click the blue 'Click Me (Trigger)' button** in the bidi component above
   - You should see `result.clicked` become `True` 🟢
   - The click count should increment

2. **Click the red 'Regular Button'** below the bidi component
   - This should trigger a rerun
   - `result.clicked` should reset to `False` 🔴
   - If it stays `True`, there's a bug! 🐛

3. **Type in the text input** or **change the selectbox**
   - These should also reset `result.clicked` to `False` 🔴

4. **Submit the form** in the bidi component (green button)
   - This should update `result.value` but `clicked` should remain `False`
""")

# Debug information
if st.checkbox("🔍 Show Debug Info"):
    st.write("### Debug Information:")
    st.write("**Bidi Result Object:**")
    st.json(
        {
            "value": bidi_result.value,
            "clicked": current_clicked,
            "type": str(type(bidi_result)),
            "hasattr_clicked": hasattr(bidi_result, "clicked"),
            "hasattr_value": hasattr(bidi_result, "value"),
        }
    )

    st.write("**Session State:**")
    st.json(dict(st.session_state))

    # Check if the result has trigger states
    if hasattr(bidi_result, "_get_trigger_states"):
        st.write("**Trigger States:**")
        st.json(bidi_result._get_trigger_states())
