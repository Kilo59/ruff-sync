# Events & Reactivity

Textual uses a powerful event-driven architecture and a reactive state system to keep the UI in sync with your data.

## Event Handlers

Naming follows the convention: `on_<widget_name>_<event_type>`.

```python
class MySidebar(Vertical):
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle any button press within the sidebar."""
        self.log(f"Button {event.button.id} was pressed!")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle specifically an Input widget change."""
        self.app.notify(f"Searching for: {event.value}")
```

## Reactive Attributes

Define `reactive` attributes to automatically trigger updates. Use `watch_<attribute_name>` to side-effect when a value changes.

```python
from textual.reactive import reactive

class Counter(Static):
    # Reactive state: UI updates whenever 'count' is modified
    count: reactive[int] = reactive(0)

    def watch_count(self, old_value: int, new_value: int) -> None:
        """Called automatically when count changes."""
        self.update(f"Current Count: {new_value}")

    def on_click(self) -> None:
        self.count += 1
```

## Message Passing

Widgets can communicate with parents via custom messages:

1. **Define a Message**:
   ```python
   from textual.message import Message
   class DataLoaded(Message):
       def __init__(self, data: list[str]) -> None:
           self.data = data
           super().__init__()
   ```
2. **Post it**: `self.post_message(DataLoaded(my_data))`
3. **Handle it in Parent**:
   ```python
   def on_data_loaded(self, event: DataLoaded) -> None:
       self.query_one(DataTable).add_rows(event.data)
   ```

## Procedure: Implementing a Search Feature

1. **Reactive Search Query**:
   ```python
   search_query: reactive[str] = reactive("")
   ```
2. **Watch the Query**:
   ```python
   def watch_search_query(self, query: str) -> None:
       """Perform search whenever the query changes."""
       results = self.search_database(query)
       self.results_container.update_results(results)
   ```
3. **Bridge from UI**:
   ```python
   def on_input_changed(self, event: Input.Changed) -> None:
       self.search_query = event.value
   ```
