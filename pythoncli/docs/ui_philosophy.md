# UI Philosophy

The UI is built using Flet (0.85+) and strictly adheres to modern Flet constraints regarding state management and component mounting.

## View Wrapper Pattern
Flet uses C++ bindings that override Python's `__getattr__` and `__setattr__`. Subclassing Flet controls (e.g., `class ModItem(ft.Container)`) and adding custom methods can lead to runtime `AttributeError` exceptions when the framework attempts to map the custom methods to the C++ layout engine.

To bypass this, components (`ModsView`, `SettingsView`, `ModItem`) are built as standard Python classes that do not inherit from Flet types. The fully constructed Flet control tree is stored inside an instance attribute (e.g., `self.view`), which is then appended to the page.

## In-Memory Control Caching (Search & Filter)
To prevent WebSocket channel clogging and layout lag during real-time queries and filtering, Flet controls are managed via an in-memory cache:
* `ModsView` maintains a `self.cached_components` dictionary containing pre-constructed `ModItem` objects.
* During initial page load or manual disk rescans (`scan_disk=True`), the mod list is populated and cached.
* During search or tag/status filtering, the controller filters the list in memory and passes it to `render_mods()`.
* instead of destroying and re-instantiating all UI controls on every single keystroke (which floods the WebSocket with thousands of rendering operations), the view simply retrieves the pre-built `ModItem` controls from the cache and mounts them.
* This reduces the search-rendering footprint to under a millisecond, completely eliminating keystroke lag.

## Flet Services vs. Overlays
In Flet 0.84+, non-visual utility features (like `FilePicker` or `Clipboard`) are formally classified as **Services** rather than UI Controls.
* **Overlays (`page.overlay`):** Intended for visual popup overlays such as `SnackBar`, `AlertDialog`, or `BottomSheet`. Placing non-visual services in the overlay list will cause the Flet C++ engine to crash at runtime with `Unknown control` errors.
* **Services (`page.services`):** Intended for invisible helper services like `FilePicker`. 

## FilePicker Lifecycle (Bypassing Timeout Exceptions)
FilePickers must be registered with the client before their asynchronous operations can be invoked.
* Creating a new `FilePicker` dynamically inside an event handler, appending it to the page, and immediately calling `picker.pick_files()` will cause a `TimeoutException` because the backend attempts to await the picker before the frontend client has completed its mounting handshake over the WebSocket.
* To prevent this, all file and directory pickers are instantiated **once** during the initialization of their respective views, appended to `page.services`, and rendered immediately on page launch. This guarantees they are fully mounted and ready for instant interaction when a user clicks a browse button.

## Unmounted Control Protection
Flet throws a `RuntimeError` if `.update()` is called on a control that is not currently mounted on the page layout. To prevent crashes during background builds when a user filters the active item out of view, all asynchronous UI updates check if the control is mounted:
```python
if self.view.page:
    try:
        self.view.update()
    except Exception:
        pass
```
