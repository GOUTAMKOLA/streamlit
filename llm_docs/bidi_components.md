# Bidi Components

- The main API is `st.components.v2.component`
  - Its entrypoint is located here: `lib/streamlit/components/v2/__init__.py`
  - Its frontend entrypoint is located here: `frontend/lib/src/components/widgets/BidiComponent/index.tsx`

## Normal Arguments:

`name`

- This component’s name, for telemetry purposes.

## Keyword-only Arguments:

### `html`

- A string with a code snippet that will be inserted on the page every time the component is called. This is useful mostly for simple static components.
- Every component must have either the html argument or the js argument, or both.

### `js`

The JS module code to load. Could be:

- A string with the actual JS
- An absolute file path
- A relative file path (relative to the file where this is called)

The JS code must declare an export default function that will be called every time the component should be drawn. This function accepts a single argument that is a JavaScript object with the following members:

- name: The name passed into component()
- data: The data passed into component()
- key: A key that is unique to this component and this instance. This can be used wherever you need a string that you know hasn’t been used anywhere else in the DOM.
- parentElement: The DOM node that you should write this component’s DOM into.
  !!!! CHANGED AND IMPLEMENTATION NEEDS TO BE UPDATED TO MATCH THIS !!!!
- setStateValue: A function that passes a value to the Python side of the component and causes the Streamlit script to rerun. This accepts two arguments: eventType and value.
- setTriggerValue: A function that passes a value to the Python side of the component and causes the Streamlit script to rerun. On subsequent reruns, this value is reset to None. This accepts two arguments: eventType and value.

IMPORTANT: Every component() must have either the html argument, or the js argument, or both.

### `css`

- The styles to load. Could be:
- A string with the actual CSS
- An absolute file path
- A relative file path (relative to the file where this is called)

To load multiple CSS files, use @import.

### `data`

- Anything that’s JSON-serializable (where any dataframe is automatically serialized using Arrow).
- This is accessible from the JS module as described in the documentation for the `js` argument.

### `isolate_styles`

- Boolean. If True, will wrap the component in a Shadow DOM so it is guaranteed to not modify the CSS styles from the rest of the page.
- Defaults to False.

### `key`

- This is accessible from the JS module as described in the documentation for the `js` argument.

### `on_{state_name}_change`

!!!! CHANGED AND IMPLEMENTATION NEEDS TO BE UPDATED TO MATCH THIS !!!!

- Any keyword argument whose name starts with on\_ will be treated as a callback function to call when the JS side calls setStateValue or setTriggerValue for that given event type.
- This is accessible from the JS module as described in the documentation for the js argument.

### `args`

!!!! CHANGED AND IMPLEMENTATION NEEDS TO BE UPDATED TO MATCH THIS !!!!

- Arguments for on\_{state_name}\_change handlers

### `kwargs`

!!!! CHANGED AND IMPLEMENTATION NEEDS TO BE UPDATED TO MATCH THIS !!!!

- Keyword arguments for on\_{state_name}\_change handlers

## Returns

!!!! CHANGED AND IMPLEMENTATION NEEDS TO BE UPDATED TO MATCH THIS !!!!

- An object containing a DeltaGenerator and the coalesced state that the JS side of the component passes back to the Python server using `setStateValue` or `setTriggerValue`.
  - Properties can be accessed either via `.property` notation or `["dictionary"]` notation.
  - For example, if a component calls `setStateValue("foo", 1)` , `setStateValue("bar", 2)`, `setTriggerValue("baz", 3)`, then the return value of `components.v2.component(...)` will be `{"delta_generator": <object>, "foo": 1, "bar": 2, "baz": 3}` at that last rerun.
  - If the user causes another rerun by interacting with a different widget, then the return value of `components.v2.component(...)` will be `{"delta_generator": <object>, "foo": 1, "bar": 2, "baz": None}` since `baz` was a trigger value.
