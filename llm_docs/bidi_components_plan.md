# Bidi Components v2 Implementation Plan

## Overview

This document outlines the technical plan for implementing the new Bidi Components v2 API, which introduces significant changes to the callback system and return type structure. The changes focus on providing a more flexible and powerful API for handling bidirectional communication between Python and JavaScript.

## Key API Changes Summary

### Python API Changes

- **Function signature**: Remove `args`/`kwargs`, add `**on_callbacks` pattern
- **Return type**: New `BidiComponentResult` containing both `DeltaGenerator` and state values
- **Callback system**: Multiple named callbacks using `on_{state_name}_change` pattern

### Frontend JavaScript API Changes

- **Interface**: Add `setStateValue<T>()` and `setTriggerValue<T>()` functions
- **Type safety**: Generic types for value preservation

## Technical Deep-Dive

### 1. State Persistence vs Triggers System Design

This is a **new fundamental concept** in Streamlit that requires careful design. Currently, all widget values persist across reruns via session state. We need to introduce a dual-mode system:

#### 1.1 Conceptual Model

- **State Values**: Persist across reruns until explicitly changed (like current widgets)
- **Trigger Values**: Available for one rerun cycle, then automatically reset to `None`

#### 1.2 Data Structure Design

**Backend Widget State Schema:**

```python
@dataclass
class BidiComponentWidgetState:
    state_values: Dict[str, Any]      # Persistent across runs
    trigger_values: Dict[str, Any]    # Reset to None each run
```

**Frontend Communication Schema:**

```typescript
interface ComponentValueUpdate {
  type: "state" | "trigger";
  eventType: string;
  value: any;
}
```

#### 1.3 Trigger Reset Strategy (Simplified)

**Core Principle**: Trigger values are automatically reset to `None` at the start of each script run, leveraging Streamlit's existing widget lifecycle.

**Simple Implementation:**

```python
@dataclass
class BidiComponentWidgetState:
    state_values: Dict[str, Any]      # Persistent across runs
    trigger_values: Dict[str, Any]    # Reset to None each run
```

**Implementation Flow:**

1. **Script Run Start**: All trigger values automatically reset to `None`
2. **During Run**: Frontend can call `setTriggerValue()` to set trigger values
3. **Component Read**: Returns current state values + current trigger values
4. **Next Script Run**: Trigger values reset to `None` again (automatic)

**Leveraging Existing Streamlit Lifecycle:**

- No need for complex tracking across script runs
- No need for cleanup logic or script_run_id tracking
- Trigger reset happens as part of normal widget state management
- Aligns with existing Streamlit patterns (similar to button behavior)

#### 1.4 Widget State Management Integration

**Current Streamlit Widget Flow:**

```
1. Widget created → register_widget() → stores in session_state
2. User interaction → setJsonValue() → updates session_state
3. Script rerun → widget re-evaluated → reads from session_state
```

**New Bidi Component Flow:**

```
1. Component created → register_bidi_widget() → stores BidiComponentWidgetState
2. Script run start → reset all trigger_values to None
3. setStateValue() → updates state_values dict (persistent)
4. setTriggerValue() → updates trigger_values dict (for current run only)
5. Component read → returns merged state_values + trigger_values
6. Next script run → trigger_values reset to None again
```

#### 1.5 Serialization/Deserialization Changes

**Current BidiComponentSerde in `lib/streamlit/components/v2/bidi_component.py`:**

```python
def deserialize(self, ui_value: str) -> BidiComponentState:
    return {"value": json.loads(ui_value)}
```

**New BidiComponentSerde:**

```python
def deserialize(self, ui_value: str) -> BidiComponentState:
    data = json.loads(ui_value)
    widget_state = get_bidi_widget_state(component_id)

    # Update state values (persistent)
    if 'state_updates' in data:
        widget_state.state_values.update(data['state_updates'])

    # Update trigger values (for current run only)
    if 'trigger_updates' in data:
        widget_state.trigger_values.update(data['trigger_updates'])

    # Merge state and trigger values for return
    result_values = widget_state.state_values.copy()
    result_values.update(widget_state.trigger_values)

    return BidiComponentState(result_values)

def reset_triggers_for_new_run(component_id: str):
    """Reset all trigger values to None at the start of each script run."""
    widget_state = get_bidi_widget_state(component_id)
    widget_state.trigger_values = {k: None for k in widget_state.trigger_values}
```

#### 1.6 Frontend Implementation Details

**Value Setting Functions in `frontend/lib/src/components/widgets/BidiComponent/BidiComponent.tsx`:**

```typescript
const setStateValue = <T>(eventType: string, value: T): void => {
  widgetMgr.setJsonValue(
    { id: componentId },
    {
      state_updates: { [eventType]: value },
    },
    { fromUi: true },
    fragmentId
  );
};

const setTriggerValue = <T>(eventType: string, value: T): void => {
  widgetMgr.setJsonValue(
    { id: componentId },
    {
      trigger_updates: { [eventType]: value },
    },
    { fromUi: true },
    fragmentId
  );
};
```

#### 1.7 Integration with Streamlit Widget Lifecycle

**Trigger Reset Integration Points:**

1. **In `lib/streamlit/runtime/state/session_state.py` - `SessionState.on_script_will_rerun()`**:

   - Leverage existing `_reset_triggers()` method at line 670
   - Extend it to handle bidi component trigger values

2. **In `lib/streamlit/runtime/scriptrunner/script_runner.py` - `ScriptRunner._run_script()`**:
   - At line 615, after `self._session_state.on_script_will_rerun()`
   - Add bidi component trigger reset logic

**Benefits:**

- Leverages existing Streamlit infrastructure
- No complex cross-run tracking required
- Automatic cleanup as part of normal lifecycle
- Consistent with other widget behaviors

### 2. Type Safety System Design

#### 2.1 Current Challenge

`setStateValue` and `setTriggerValue` accept `any` type for values, which reduces type safety.

#### 2.2 Type Safety Strategy

```typescript
setStateValue<T>(eventType: string, value: T): void
setTriggerValue<T>(eventType: string, value: T): void
```

### 3. Enhanced Return Type Design

#### 3.1 BidiComponentResult Requirements

- Must contain both a `DeltaGenerator` and the coalesced component state
- Support both `.property` and `["dictionary"]` access patterns
- Handle state values (persistent) vs trigger values (reset to None on rerun)

**Implementation:**

```python
class BidiComponentResult(AttributeDictionary):
    """
    Result object from st.components.v2.component containing both
    a DeltaGenerator and component state values.
    """

    def __init__(self, delta_generator: DeltaGenerator, state_values: dict):
        # Store delta_generator as a special property
        super().__init__({"delta_generator": delta_generator, **state_values})

    @property
    def delta_generator(self) -> DeltaGenerator:
        return self["delta_generator"]
```

#### 3.2 Return Value Composition

```python
# Example usage after implementation:
result = st.components.v2.component(
    "my_component",
    data={"initial": "data"},
    on_click_change=handle_click,
    on_value_change=handle_value
)

# Access patterns:
result.delta_generator.markdown("Additional content")  # Delta generator
result["click"]  # Dictionary access
result.value     # Property access
result.click     # Property access for click events
```

### 4. Callback System Design

#### 4.1 Enhanced Callback Pattern

- Focus on `on_{state_name}_change` pattern for event handling
- Callbacks receive the event value directly as their single argument
- Multiple callbacks per component supported

**Implementation Strategy:**

```python
def parse_callbacks(**kwargs) -> Dict[str, WidgetCallback]:
    """Parse on_* keyword arguments into event callbacks."""
    callbacks = {}
    for key, value in kwargs.items():
        if key.startswith("on_") and key.endswith("_change") and callable(value):
            event_name = key[3:-7]  # Remove "on_" and "_change"
            callbacks[event_name] = value
    return callbacks
```

### 5. Error Handling Strategy

#### 5.1 Minimal Required Error Handling

- Implement basic error propagation and user feedback
- Focus on functionality first; comprehensive error handling can be enhanced later

**Key Error Scenarios:**

- Invalid event types in callbacks
- Serialization/deserialization failures
- Component registration errors
- Type safety violations

---

## Implementation Checklist

### Phase 1: Backend Foundation

#### Core Data Structures

- [x] Create `BidiComponentResult` class with AttributeDictionary inheritance in `lib/streamlit/components/v2/bidi_component.py`
- [x] Create `BidiComponentWidgetState` dataclass for dual-mode state management in `lib/streamlit/components/v2/bidi_component.py`
- [x] Implement trigger reset mechanism by extending `SessionState._reset_triggers()` in `lib/streamlit/runtime/state/session_state.py`

#### Function Signature Updates

- [x] Update `component()` function signature in `lib/streamlit/components/v2/__init__.py`
- [x] Implement callback parsing logic for `on_{state_name}_change` pattern in `BidiComponentMixin.bidi_component()`
- [x] Remove `args`/`kwargs` from public API in `lib/streamlit/components/v2/bidi_component.py`

#### Protobuf Changes

- [x] Update `proto/streamlit/proto/BidiComponent.proto` for state vs trigger values (if needed)

### Phase 2: State Management System

#### Widget Registration

- [ ] Create `register_bidi_widget()` function for dual-mode state management in `lib/streamlit/runtime/state/widgets.py`
- [ ] Update `BidiComponentMixin.bidi_component()` in `lib/streamlit/components/v2/bidi_component.py` to handle new callback system
- [ ] Modify return type from `BidiComponentState` to `BidiComponentResult` in `lib/streamlit/components/v2/bidi_component.py`

#### Serialization/Deserialization

- [ ] Implement new `BidiComponentSerde` with state/trigger differentiation in `lib/streamlit/components/v2/bidi_component.py`
- [ ] Extend `SessionState._reset_triggers()` method in `lib/streamlit/runtime/state/session_state.py` to handle bidi component triggers
- [ ] Update widget state management to handle multiple callbacks in `lib/streamlit/runtime/state/session_state.py`

#### Memory Management

- [ ] Implement trigger value cleanup mechanism in `SessionState.on_script_will_rerun()` in `lib/streamlit/runtime/state/session_state.py`
- [ ] Add trigger reset integration in `ScriptRunner._run_script()` in `lib/streamlit/runtime/scriptrunner/script_runner.py`
- [ ] Handle memory cleanup for long-running sessions leveraging existing cleanup in `SessionState.on_script_finished()`

### Phase 3: Frontend Integration

#### TypeScript Interface Updates

- [ ] Update `StBidiComponentV2Args` interface in `frontend/lib/src/components/widgets/BidiComponent/types.ts`:
  - Remove `childContainerIDs`
  - Add `setStateValue<T>` and `setTriggerValue<T>` functions

#### Component Implementation

- [ ] Update `loadAndRunModule` function in `frontend/lib/src/components/widgets/BidiComponent/BidiComponent.tsx`
- [ ] Implement `setStateValue` and `setTriggerValue` functions with type safety
- [ ] Update handler generation logic to use new callback system
- [ ] Remove hardcoded handler logic (like special `onClick` handling in lines 106-115)

#### Context Updates

- [ ] Update `BidiComponentContext` shape if needed for new callback system in `frontend/lib/src/components/widgets/BidiComponent/BidiComponentContext.tsx`
- [ ] Ensure proper widget state manager integration

#### Widget State Manager Integration

- [ ] Support differentiation between state values and trigger values in `frontend/lib/src/WidgetStateManager.ts`
- [ ] Implement trigger value reset logic on reruns
- [ ] Handle multiple callback types per component

### Phase 4: Testing & Documentation

#### Backend Testing

- [ ] Update existing tests in `lib/tests/streamlit/components/v2/`
- [ ] Add comprehensive tests for new callback system
- [ ] Add tests for state vs trigger value behavior
- [ ] Add tests for new return type interface
- [ ] Test trigger reset mechanism integrated with script lifecycle

#### Frontend Testing

- [ ] Add frontend tests for new JS interface
- [ ] Test type safety with generic functions
- [ ] Test state/trigger value differentiation
- [ ] Add integration tests for callback system

#### Documentation

- [ ] Document API changes clearly
- [ ] Create migration guide for any existing v2 components (if any)
- [ ] Update API documentation for new return type and callback patterns
- [ ] Document type safety features and best practices

## Implementation Notes

### Performance Considerations

- Focus on functionality first; performance optimizations can be addressed later
- Use existing Streamlit infrastructure (session state lifecycle) rather than creating new systems
- Memory cleanup for trigger values is important for long-running sessions

### Technical Dependencies

- Leverage existing trigger reset mechanism in `lib/streamlit/runtime/state/session_state.py`
- Build on existing widget state management system
- Use existing `AttributeDictionary` for return type implementation

### Phase 1 Implementation Notes

**Completed:**

- ✅ `BidiComponentResult` class: Successfully implemented with AttributeDictionary inheritance, supporting both `.property` and `["dictionary"]` access patterns. The class stores the DeltaGenerator as a special property while merging state values.
- ✅ `BidiComponentWidgetState` dataclass: Implemented with separate `state_values` and `trigger_values` dictionaries to support the dual-mode state management system.
- ✅ Trigger reset mechanism: Extended `SessionState._reset_triggers()` to include `_reset_bidi_component_triggers()` method that safely resets trigger values to None while leveraging existing Streamlit lifecycle.

**Implementation Considerations:**

- Used defensive programming in `_reset_bidi_component_triggers()` to handle cases where widget state doesn't have expected structure
- Added circular import protection by importing `BidiComponentWidgetState` locally within the reset method
- The trigger reset integration leverages existing Streamlit infrastructure rather than creating new systems

**Function Signature Updates - Completed:**

- ✅ Updated `component()` function in `lib/streamlit/components/v2/__init__.py` to use `**on_callbacks: WidgetCallback` pattern instead of `on_change` and `**kwargs`
- ✅ Implemented callback parsing logic using `on_{state_name}_change` pattern (e.g., `on_click_change`, `on_value_change`)
- ✅ Removed `*args` and replaced old callback handling in `BidiComponentMixin.bidi_component()`
- ✅ Added comprehensive docstring with parameter descriptions
- ✅ Added helper function `parse_callbacks()` for reusable callback parsing logic

**Protobuf Changes - Completed:**

- ✅ Added documentation comment to `BidiComponent.proto` indicating future extension for state vs trigger differentiation
- ✅ Current schema supports the Phase 1 implementation; more extensive changes will be needed in Phase 2 for state/trigger value differentiation

**Breaking Changes:**

- The callback API now requires `on_{event_name}_change` pattern instead of `on_{event_name}`
- Updated tests to reflect new callback pattern (e.g., `on_value_change` instead of `on_change`)

**Backwards Compatibility:**

- Function signature changes are breaking but necessary for the new API design
- All existing tests pass with minimal updates to use new callback patterns

**Implementation Issues Identified:**

- ⚠️ **Return Type Change Pending**: The plan calls for changing return type from `BidiComponentState` to `BidiComponentResult`, but this was not implemented in Phase 1 to avoid breaking existing functionality. This change should be addressed in a later phase when the full state management system is implemented.
- ⚠️ **Phase 2 Dependency**: The new callback parsing logic is in place, but the actual state vs trigger value differentiation requires the Phase 2 state management system implementation.

This plan provides a comprehensive roadmap for implementing the Bidi Components v2 API changes while leveraging existing Streamlit infrastructure and maintaining code quality.
