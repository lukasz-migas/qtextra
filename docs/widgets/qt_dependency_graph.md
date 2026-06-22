# QtDependencyGraph

Scrollable stateful task graphs with automatic dependency layout and relationship highlighting.

## Screenshot

{{ show_example('qt_dependency_graph.py', 920) }}

## Example

Source: `examples/qt_dependency_graph.py`

{{ include_example('qt_dependency_graph.py') }}
## Notes

- Dependency graphs are read-only and validate that the supplied task topology is acyclic.
- Click a task to highlight every upstream dependency and downstream dependant.

## API

{{ show_members('qtextra.widgets.qt_dependency_graph.DependencyGraphNode') }}

{{ show_members('qtextra.widgets.qt_dependency_graph.QtDependencyGraph') }}
