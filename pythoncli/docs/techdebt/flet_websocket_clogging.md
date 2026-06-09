# Technical Debt: Flet WebSocket Clogging under High Log Throughput

## 1. Real-Time Log Clogging
### Status: PARTIALLY MITIGATED (Compiler), FULLY RESOLVED (Search & Filter)

### Description
To output live build logs, `ModsView.execute_pipeline` reads the stdout of the compiler and calls `self.write_log()` on every line, which appends an `ft.Text` control to `log_view` and executes `page.update()`.

During massive compilation phases (like initial shader compiles), Unreal Engine can print hundreds of log lines per second. Flooding the Flet local WebSocket server with hundreds of micro-updates per second can clog the channel, leading to UI lag, desynchronized progress bars, or memory leaks on the client webview.

### Resolution (Search & Filter)
The severe WebSocket clogging that occurred during real-time search queries and tag filtering has been **completely resolved**. 

Previously, `render_mods()` cleared the list view and re-instantiated hundreds of complex `ModItem` and `ModDetails` controls on every single keystroke. This flooded the WebSocket with massive layout modifications, causing the browser client to freeze and leaving old elements stranded on the screen.

This has been fixed by implementing an **In-Memory UI Component Cache** inside `ModsView`:
* UI controls are built and cached once during initial disk rescans.
* Keypresses now simply perform an $O(1)$ memory lookup to retrieve and rearrange the already existing control instances, bypassing control recreation entirely.
* This reduces the keystroke rendering footprint to zero overhead, allowing instantaneous search results.

### Outstanding Mitigation (Compiler Logs)
For compiler logs, the risk of high-frequency logging is mitigated by an unbuffered async subprocess runner (`utils/builder/pipeline_runner.py`) which batches WebSocket updates. It streams incoming logs to the Python console instantly but caps Flet UI log updates to a maximum frequency of **100ms** to prevent flooding the WebSocket channel.