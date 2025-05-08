/**
 * Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022-2025)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// 👇👇👇 This is just a wrapper function that passes arguments to your
// plain vanilla Slider component.
export default function main(component) {
  const sliderEl = makeSlider(
    component.data.label,
    component.data.min,
    component.data.max,
    component.data.value,
    (el) => component.onChange(el.target.value)
  );

  component.parentElement.append(sliderEl);
}

// This a plain vanilla Slider component that knows nothing
// about Streamlit.
function makeSlider(label, min, max, value, callback) {
  const divEl = document.createElement("div");

  const inputEl = document.createElement("input");
  inputEl.setAttribute("type", "range");
  inputEl.setAttribute("min", min);
  inputEl.setAttribute("max", max);
  inputEl.setAttribute("value", value);
  inputEl.addEventListener("change", callback);
  divEl.append(inputEl);

  const labelEl = document.createElement("label");
  const text = document.createTextNode(label);
  labelEl.append(text);
  divEl.append(labelEl);

  return divEl;
}
