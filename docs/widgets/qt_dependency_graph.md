# QtDependencyGraph

Interactive task graphs with movable nodes, custom states, icons, and automatic layout.

## Screenshot

{{ show_example('qt_dependency_graph.py', 920) }}

## Example

Source: `examples/qt_dependency_graph.py`

{{ include_example('qt_dependency_graph.py') }}
## Notes

- Dependency graphs are read-only and validate that the supplied task topology is acyclic.
- State names are arbitrary strings configured through a state-to-color mapping.
- Drag nodes to reposition them, with live edge routing and optional dotted-grid snapping.
- Position APIs support runtime layout persistence; reset layout restores the automatic topology.
- Drag empty canvas space to pan, use the wheel to zoom, or use the keyboard shortcuts.
- Nodes accept optional `QIcon` values or qtextra icon aliases.
- Click a task to highlight every upstream dependency and downstream dependant.
- Nodes with the same non-empty `group` collapse into an aggregate card by default; double-click the group to expand it or a member to collapse it.

## API

{{ show_members('qtextra.widgets.qt_dependency_graph.DependencyGraphNode') }}

{{ show_members('qtextra.widgets.qt_dependency_graph.QtDependencyGraph') }}
