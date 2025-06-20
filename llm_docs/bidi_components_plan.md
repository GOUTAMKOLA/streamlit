# Bidi Components v2 – Streamlined Implementation Plan

> This revision removes bespoke data-structures and lifecycle hooks that already exist in Streamlit. The plan below shows how to deliver the new Python/JS callback API **using today's widget & trigger plumbing** with only small, localised changes.

---

## 0 TL;DR

We _will_ touch the codebase – but in the most incremental way possible. The table below sums it up:

| Area                                   | Change                                                                         | # LOC |
| -------------------------------------- | ------------------------------------------------------------------------------ | ----- |
| Python `bidi_component.py`             | `BidiComponentResult`, multi-callback parsing, widget-id scheme, Serde tweaks  | ≈ 70  |
| Python `session_state._reset_triggers` | Add support for the **optional** `json_trigger_value` field                    | ≈ 10  |
| Protobuf                               | Add `json_trigger_value` (string) field (one line)                             | —     |
| Front-end `BidiComponent.tsx`          | Build `triggerId = baseId + "__" + event` and send value via `setTriggerValue` | ≈ 20  |
| Unit + E2E tests                       | Update assertions, add trigger-reset test                                      | —     |

Total footprint < 120 LOC (+ proto). No dual worlds; we keep using the widget engine that already exists.

---

## 1 Conceptual model (product-spec aligned)

- **State values** (persistent) – stored in a base widget (`json_value`).
- **Trigger values** (one-shot) – stored in _per-event_ widgets that auto-reset; needs to transport arbitrary JSON payloads.

Because current trigger widget types (`trigger_value`, `string_trigger_value`) reset automatically, we simply add **`json_trigger_value`** (string that carries JSON payload) so that any data type is possible. We hook this new type into the tiny `_reset_triggers` `elif` block.

---

## 2 Widget-ID scheme & mapping

```
<component_id>              →  persistent widget (json_value)
<component_id>__<event>     →  trigger widget  (json_trigger_value)   # NEW
```

This lets us:

1. Keep an independent trigger channel per event (so simultaneous triggers are OK).
2. Reuse existing callback dispatch ‑ we register _each_ trigger widget with its own callback dict `{ "click": user_fn }` or `{ "change": user_fn }`.
3. Achieve automatic reset (handled after we add the new value_type).

### Technical details

- **Uniqueness & determinism**: The `component_id` originates from the `WidgetStateManager` and is already unique per component instance. Appending `__<event>` is therefore collision-free and **idempotent** – generating the same ID every time we render the same component+event pair.
- **Delimiter choice**: We use a double underscore (`__`) because the core widget engine already forbids this sequence inside `component_id` itself. This guarantees that a simple `split("__", 1)` cleanly separates the base and event portions on both the Python _and_ TS sides.
- **Round-trip serialisation**: All IDs remain plain ASCII so they flow unchanged through protobuf and JSON layers. No additional escaping is necessary.
- **Back-compat**: Existing components (which never generate IDs with the `__` pattern) remain unaffected. The new suffix appears only when a component uses `setTriggerValue` / `setStateValue` with a custom event name.
- **Concurrency**: Because every event sits in its own widget, two JS events fired in the same millisecond won't stomp on each other – the widget engine queues two distinct `json_trigger_value` updates.
- **Garbage collection**: When a component is removed from the DOM, the widget engine already prunes its state values. The `__<event>` widgets disappear together with the base widget because the key prefix is identical.

### Implementation checklist

Below is the recommended dev sequence – each checkbox can be shipped as an incremental PR:

- [x] **Shared constant**: Introduce `EVENT_DELIM = "__"` in both the Python (`lib/streamlit/components/v2/bidi_component.py`) and TS (`frontend/lib/src/components/widgets/BidiComponent/constants.ts`) layers to avoid magic strings.
  - _TDD_:
    - `lib/tests/streamlit/components/test_bidi_constants.py` → asserts that `EVENT_DELIM` exists and equals `"__"`.
    - `frontend/lib/src/components/widgets/BidiComponent/constants.test.ts` → same assertion on the TS constant export.
- [x] **Backend ID builder**: Add helper `def make_trigger_id(base: str, event: str) -> str` and refactor `BidiComponentMixin` to use it.
  - _TDD_: `lib/tests/streamlit/components/test_bidi_id_builder.py` → covers happy-path, illegal chars, and idempotency.
- [x] **Frontend ID builder**: Mirror the helper in TS and update `BidiComponent.tsx` handler factory so that every call to `setTriggerValue` uses the suffixed ID.
  - _TDD_: `frontend/lib/src/components/widgets/BidiComponent/idBuilder.test.ts` → validates parity with Python logic via a set of (base,event) fixtures.
- [x] **WidgetStateManager.update()**: Overload `setTriggerValue` to accept an _optional_ `value` argument that maps into the new `json_trigger_value` protobuf field.
- _TDD_: `frontend/lib/src/components/widgets/WidgetStateManager/setTriggerValue.test.ts` → ensures the protobuf field is populated and that legacy (no-value) calls still work.
- [x] **SessionState reset hook**: Extend `_reset_triggers` with the `json_trigger_value` clause while keeping existing behaviour untouched.
  - _TDD_: `lib/tests/streamlit/session_state/test_reset_triggers.py` → simulates a run cycle and asserts the value resets to `None`.

---

## 3 Backend changes

### 3.1 `BidiComponentResult`

```python
class BidiComponentResult(AttributeDictionary):
    def __init__(self, dg: DeltaGenerator, state_vals: dict[str, Any], trigger_vals: dict[str, Any]):
        super().__init__({ "delta_generator": dg, **state_vals, **trigger_vals })

    @property
    def delta_generator(self) -> "DeltaGenerator":
        return self["delta_generator"]
```

- _TDD_: `lib/tests/streamlit/components/test_bidi_component_result.py` → verifies that the merged dict exposes both attribute & key access and that the `delta_generator` property returns the same object passed to `__init__`.

### 3.2 `BidiComponentMixin.bidi_component()`

1. **Parse callbacks**: for every kwarg that matches the regex `^on_(.+)_change$`, capture the _event name_ (group 1) and function. This supports unlimited arbitrary event names:
   ```python
   callbacks_by_event: dict[str, WidgetCallback] = {}
   for k, v in kwargs.items():
       if k.startswith("on_") and k.endswith("_change") and callable(v):
           callbacks_by_event[k[3:-7]] = v          # strip on_/ _change
   ```
2. **Register _state_ widget** – one per component (holds a dict of all persistent event values).
3. **Register _trigger_ widgets** – _one per event_ (even if no callback supplied, so the value shows up in result):
   ```python
   for evt, cb in callbacks_by_event.items():
       trig_id = f"{base_id}__{evt}"
       register_widget(
           trig_id,
           deserializer=lambda s: json.loads(s) if s else None,
           serializer=lambda v: json.dumps(v),
           ctx=ctx,
           callbacks={"change": cb},   # click vs change irrelevant; value change fires rerun
           value_type="json_trigger_value",
       )
   ```
4. **Result assembly** – collect _all_ current triggers (even those with no callback):
   ```python
   trigger_vals = {
       evt: ctx.session_state.get(f"{base_id}__{evt}")
       for evt in events_seen_from_js_or_kwargs
   }
   return BidiComponentResult(self.dg, state_meta.value, trigger_vals)
   ```

- _TDD_: `lib/tests/streamlit/components/test_bidi_component_mixin.py` → covers:
  - `on_*_change` parsing into `callbacks_by_event`.
  - Correct generation of `make_trigger_id`-style IDs.
  - Registration of widgets with expected `value_type`.
  - Returned `BidiComponentResult` contains both state & trigger keys.

### 3.3 `BidiComponentSerde`

No big change – it still converts `json_value` to a Python `dict`. JS will be sending `{ "state_updates": {…} }`; here we just return that dict and let the user code consume it.

- _TDD_: `lib/tests/streamlit/components/test_bidi_component_serde.py` → round-trips example `json_value` payloads and asserts Python dict output.

### 3.4 `session_state._reset_triggers`

Add one `elif` in both loops:

```python
elif metadata.value_type == "json_trigger_value":
    self._new_widget_state[state_id] = Value(None)
    self._old_state[state_id] = None
```

- _TDD_: see `lib/tests/streamlit/session_state/test_reset_triggers.py` (already listed) – ensure reset occurs only for the new value_type and leaves others intact.

---

## 4 Protobuf tweak

In `proto/WidgetStates.proto` add

```protobuf
string json_trigger_value = 15;
```

(choosing next available field number). Regenerate protos (`scripts/proto_codegen.sh`).

- _TDD_: `lib/tests/proto/test_widgetstates_proto.py` → uses the generated Python proto module to construct a `WidgetStates` message, sets `json_trigger_value`, serialises & deserialises, and checks the field survives.

---

## 5 Frontend changes

### 5.1 `BidiComponent.tsx`

Inside the existing handler-factory change:

```ts
const triggerId = `${componentIdForWidgetMgr}__${eventName}`;
void widgetMgr.setTriggerValue(
  { id: triggerId },
  JSON.stringify(value ?? true) as any, // WidgetStateManager currently ignores this arg; value carried via proto field
  fragmentId
);
```

(Note: we will overload `setTriggerValue` to accept a second `value` that will be stored in the `json_trigger_value` field.) Implementation is a 3-line change in `WidgetStateManager.setTriggerValue`.

- _TDD_: `frontend/lib/src/components/widgets/BidiComponent/triggerPath.test.tsx` → mounts the component, fires a dummy event, and asserts that `widgetMgr.setTriggerValue` is called with the suffixed ID and the JSON-stringified payload.

### 5.2 Optional sugar helpers

Expose to component authors:

```ts
setStateValue(evt, val);
setTriggerValue(evt, val);
```

Already implied by product spec – just forward to logic above.

- _TDD_: `frontend/lib/src/components/widgets/BidiComponent/sugarHelpers.test.ts` → spies on the internal helper and verifies correct delegation, argument order, and defaulting to `true` when `val` is omitted.

---

## 6 Multi-callback semantics

Because each _event_ has its own widget we get **per-event callbacks for free**:

- For `on_click_change` we attach to trigger widget's `"click"` key.
- For `on_value_change` (persistent) we attach to state widget's `"change"` key (already in place), but we must tweak `_widget_changed` detection to work with dicts – easy: compare full dicts (already does deep compare).

Multiple callbacks on the _same_ event (rare) can still be handled by allowing the user to pass a list or by registering chained functions, but **spec only calls for one callback per event**, so no extra work.

- _TDD_:
  - Backend → `lib/tests/streamlit/components/test_bidi_multi_callback.py` → simulates two trigger widgets, ensures only their respective callbacks fire, and that order/duplication rules hold.
  - Frontend → `frontend/lib/src/components/widgets/BidiComponent/multiCallback.test.ts` → verifies that multiple `setTriggerValue` calls in rapid succession map to distinct widget IDs.

---

## 7 Testing

1. **Backend**: add unit tests covering
   - JSON trigger resets to `None` between runs. (`test_reset_triggers.py`)
   - Callbacks fire exactly once. (`test_bidi_multi_callback.py`)
2. **Frontend**: update existing BidiComponent tests to expect suffixed widget ids (`triggerPath.test.tsx`) and verify helper utilities (`sugarHelpers.test.ts`).
3. **Playwright**: reuse current `trigger_reset_test` after renaming the trigger id expectation.

---

## 8 End-to-end spec example

```python
out = st.components.v2.component(
    "my_component",
    html="<div>Some html</div>",
    on_my_stateful_value_change=lambda v: st.write("state now", v),
    on_my_trigger_change=lambda _: st.write("trigger fired"),
)
```

Assume the JS side does:

```js
setStateValue("my_stateful_value", "hello");
setTriggerValue("my_trigger");
```

Return value **during the rerun invoked by setTriggerValue**:

```python
{
  "delta_generator": <DeltaGenerator>,
  "my_stateful_value": "hello",   # persistent
  "my_trigger": True               # trigger fired
}
```

Return value **on a subsequent unrelated rerun**:

```python
{
  "delta_generator": <DeltaGenerator>,
  "my_stateful_value": "hello",
  "my_trigger": None   # auto-reset by SessionState._reset_triggers
}
```

Callbacks:

- `on_my_stateful_value_change` called whenever the _value_ differs from previous run.
- `on_my_trigger_change` called exactly when `my_trigger` widget's `json_trigger_value` is set (same run where `True` is observed).
