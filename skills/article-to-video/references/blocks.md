# Blocks: the catalog

Read this at Step 5 of the skill, when you select the blocks for a chapter. The blocks are in `videogen.blocks`. Each block builds the mobjects. The scene shows the parts on the words of the narration. `examples/demo/scenes/` of the template has an example for each block.

## Charts

Each chart is a `Chart`: `axes`, `frame` (ticks, grid, titles), `marks` (the data), `labels` (the direct labels), `title`, `legend`, `note`. `chart.shell()` gives the parts to show first (axes, frame, title, legend, note). `chart.everything()` gives all.

The common arguments:

| Argument | Meaning |
|---|---|
| `center=(x, y)` | center of the axes. Default: a position that keeps the title at the top and the band of the subtitles at the bottom free |
| `width`, `height` | of the axes, in scene units. The frame is 14.2 by 8 |
| `y_ticks`, `x_ticks` | the values with a label |
| `y_fmt`, `x_fmt`, `value_fmt` | functions number to text, for LaTeX: for example `self.lang.percent` |
| `y_label`, `x_label`, `title` | text in LaTeX form |
| `note` | text below the chart: the source, or "Sample data" |
| `legend_entries` | list of `(color, label)`, or `True` to make it from the data |

The default positions of the blocks keep the band at the bottom free (`y < -2.9`) and the corner of the logo at the top right. When you give a `center`, a `height` or a large `width`, the note under the chart and the labels of the axis are the first to enter the band: `videogen check` reports them.

| Block | For | Data |
|---|---|---|
| `column_chart(categories, values, y_range, ...)` | a comparison of a few values from zero | `categories` names, `values` numbers, `y_range` `(0, maximum)` |
| `ranked_bars(rows, x_range, ...)` | a few horizontal bars, the largest first | rows `(label, sublabel or None, value, color)` |
| `dot_plot(rows, x_range, ...)` | values near each other, on an axis that does not start at zero | rows `(label, value, color)` |
| `line_chart(series, x_range, y_range, ...)` | a trend, one or more series | series `(label, color, [(x, y), ...])`. `reference=(y, label)` adds a dashed line |
| `small_multiples(panels, x_range, y_range, ...)` | two to four line charts on the same axis | panels `(title, series)` |
| `qualitative_curves(axes, curves)` | a trend with no numbers | curves `(color, function)`. Put a note on the chart |

Example:

```python
chart = column_chart(["A", "B"], [42, 58], (0, 80), y_ticks=[0, 40, 80], y_fmt=self.lang.percent,
                     title="Score after one step", note="Sample data.")
self.play(*[FadeIn(part, shift=UP * 0.06) for part in chart.shell()], run_time=1.4)
self.play(LaggedStart(*[GrowFromEdge(bar, DOWN) for bar in chart.marks], lag_ratio=0.15))
self.play(FadeIn(chart.labels))
```

## Diagrams

| Block | For | Form |
|---|---|---|
| `pipeline(stages, loop=...)` | the steps of a process in a row | stages `(label, color)` or `(label, color, note)`. `loop=(from, to, label)` adds the arrow that goes back |
| `flow(nodes, edges, loops, paths)` | boxes with names and arrows | nodes `(name, label, color, x, y[, note])`. edges `(start, end[, color[, style]])`, style `arrow`, `line` or `dashed`. loops `(name, side, color)`. paths `([[x, y], ...], color)` |
| `feedback_loop(box, side, color)` | a loop on one box | side `below`, `above`, `left` or `right` |
| `compare_table(columns, rows, ...)` | a comparison of options | columns `(title, subtitle or None)`, rows = labels. `table.row(index, values)` makes the cells of one row |
| `stack(count, width, height, color)` (in `videogen.theme`) | a pile of layers, from the bottom to the top | `sweep(stack)` makes a signal that goes through the layers |

`flow` and `pipeline` return objects with named parts: `diagram.boxes["model"]`, `diagram.arrows`, `diagram.loops`, `line.stages`, `line.loop`, `line.loop_label`.

## Text on the stage

| Block | For | Form |
|---|---|---|
| `quote(lines, attribution)` | a quotation with its source | `{{a phrase}}` isolates a phrase: `quote.part(line, index)` |
| `stat_tiles(items, centers)` | one to three key numbers | items `(value in LaTeX, label)`, centers `(x, y)` |
| `card(heading, lines, color)` and `cards(items, centers)` | a note, a definition, a limitation | lines: a list, or one string |
| `statement(lines)` | the conclusion of a part, at the center | lines of text |
| `takeaways(points)` | the points of the summary | points `(title, detail, color)`. `points.row(i)` is one point |
| `side_brace(x, y_low, y_high, label)` | a brace at the right of a group of lines | |
| `credits(title, blocks)` | the last screen | blocks `(heading, lines)` |

## Helpers of `videogen.theme`

`T` (LaTeX text), `M` (math), `plain` (text with special characters), `lines` and `rows` (blocks of lines), `LabeledBox` (a box with a label), `slab`, `arr` (arrow), `path_arrow` (arrow on a polyline), `wire` (lines), `marker` (a point of a chart), `legend`, `appear`, `sweep`, `focus`, `glow`.

## Limits of the automatic verification

`videogen check` compares the boxes of the lines of text. It finds text out of the frame, text on text, text in the band of the subtitles and text under the logo. It does not see a line on text, a color that does not read, or a visual at the wrong position: look at the contact sheets. A visual without text in the band of the subtitles shows only in the sheets of the film (`videogen sheet --film`), because the preview has no subtitles.
