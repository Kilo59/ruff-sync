# Styling & Layout (TCSS)

Textual uses **TCSS** (Textual Cascading Style Sheets) for design. It is similar to web CSS but optimized for the terminal grid.

## Core Units

- **`fr`**: Fractional units (e.g., `1fr`, `2fr`). Divides available space proportionally.
- **`%`**: Percentage of the parent container's dimension.
- **`vh` / `vw`**: Percentage of the entire terminal window height/width.
- **Integers**: Represent exact terminal character cells (e.g., `width: 20;`).

- **`Vertical`**: Stack widgets top-to-bottom.
- **`Horizontal`**: Align widgets left-to-right.
- **`Grid`**: A flexible 2D grid layout. Define `grid-size`, `grid-columns`, and `grid-rows`.

## New CSS Rules (v8.x.x)

- **`pointer`**: Change the mouse cursor style (e.g., `pointer: pointer;`, `pointer: text;`).
- **`background-tint`**: Apply a translucent color over the background (e.g., `background-tint: $primary 20%;`).
- **`text-padding`**: Simplified padding for text content within a widget (e.g., `text-padding: 1 2;`).
- **`scroll-bar-visibility`**: Control when scrollbars are shown (`auto`, `visible`, `hidden`).
- **`position`**: Support for `relative` and `absolute` positioning.

## Procedure: Rapid Styling

1. **Assign IDs or Classes**:
   ```python
   yield Button("Save", id="save-btn", classes="primary-action")
   ```
2. **Define TCSS**:
   ```css
   .primary-action {
       background: $accent;
       color: $text;
       text-style: bold;
       width: 100%;
   }

   #save-btn {
       border: heavy $success;
   }
   ```
3. **Reference CSS in App**:
   ```python
   class MyApp(App):
       CSS_PATH = "styles.tcss"  # Relative to the Python file
   ```

## Built-in Design System

Textual includes a set of semantic variables (`$primary`, `$secondary`, `$accent`, `$error`, `$success`) that automatically adapt to the user's terminal theme.

> [!TIP]
> Use `textual console` or `textual run --dev` to see live styling updates without restarting the application.
