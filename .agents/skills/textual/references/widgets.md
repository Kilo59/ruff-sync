# Widget Library

Textual includes a rich set of built-in widgets. Always check `textual.widgets` before building your own.

## Content & Navigation

- **`Header`**: Standard title bar with optional clock.
- **`Footer`**: Keybinding bar (automatically populated from `BINDINGS`).
- **`Static`**: Pure text or basic content. Use **`content`** (v8.x.x) for raw renderable or `markup=True`.
- **`Link`**: (v8.x.x) New widget for clickable URLs.
- **`ProgressBar`**: Real-time progress tracking.

## Interaction

- **`Button`**: Standard clickable button. Variants: `success`, `error`, `primary`, `warning`.
- **`Input`**: Text entry field. Events: `Changed`, `Submitted`.
- **`MaskedInput`**: (v8.x.x) New widget for formatted inputs (e.g. phones, CC, etc.).
- **`Checkbox`** / **`Switch`**: Boolean state inputs.
- **`Select`**: Dropdown selection. Sentinel: **`Select.NULL`** (v8.x.x).

## Data & Selection

### `DataTable`
High-performance grid for tabular data.

```python
table = self.query_one(DataTable)
table.add_columns("ID", "Name", "Score")
table.add_row("1", "Alice", "100")
```

### `ListView` & `ListItem`
Scrollable lists of items.

```python
list_view = self.query_one(ListView)
list_view.append(ListItem(Static("Item One")))
```

## Procedures

### Adding Data to a Table

1. **Clear existing rows**: `table.clear()`
2. **Batch add rows**: `table.add_rows(data_generator_or_list)`
3. **Control selection**: `table.cursor_type = "row"` (default is `"cell"`)

### Handling Keyboard Input

Use the `on_key` handler for low-level input:

```python
def on_key(self, event: events.Key) -> None:
    if event.key == "ctrl+s":
        self.save_data()
```

> [!TIP]
> Use `BINDINGS` in your `App` or `Screen` class for most navigation tasks. Textual manages the labels and shortcuts in the `Footer` for you.

### `ModalScreen` & Overlays
Modals are screens with a transparent or dim background that overlay the main app.
```python
from textual.screen import ModalScreen
from textual.app import App

class OmniboxScreen(ModalScreen[str]):
    # A modal screen that returns a `str` when dismissed.
    def compose(self) -> ComposeResult:
        # yield your input/search widgets here
        yield Input(placeholder="Search...")

    # Dismiss the screen and return data
    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

# In the main App or Screen:
def on_key(self, event: events.Key) -> None:
    if event.key == "ctrl+p":
        self.push_screen(OmniboxScreen(), self.handle_omnibox_result)

def handle_omnibox_result(self, result: str | None) -> None:
    if result:
        print(f"Selected: {result}")
```
