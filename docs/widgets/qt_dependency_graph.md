# QtDependencyGraph

Scrollable task graphs with custom state colors, automatic layout, and relationship highlighting.

## Screenshot

{{ show_example('qt_dependency_graph.py', 920) }}

## Example

Source: `examples/qt_dependency_graph.py`

{{ include_example('qt_dependency_graph.py') }}
## Notes

- Dependency graphs are read-only and validate that the supplied task topology is acyclic.
- State names are arbitrary strings configured through a state-to-color mapping.
- Drag empty canvas space to pan, use the wheel to zoom around the cursor, or call the public zoom methods.
- Click a task to highlight every upstream dependency and downstream dependant.

## API

{{ show_members('qtextra.widgets.qt_dependency_graph.DependencyGraphNode') }}

{{ show_members('qtextra.widgets.qt_dependency_graph.QtDependencyGraph') }}
