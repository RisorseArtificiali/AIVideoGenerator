"""The script of the demo video. All the numbers are sample data."""

from collections import namedtuple

Beat = namedtuple("Beat", "key text visual")

SCENE_ORDER = ["ch00", "ch01", "ch02", "ch03"]

CHAPTERS = {
    "ch00": ("", ""),
    "ch01": ("1", "Charts"),
    "ch02": ("2", "Diagrams"),
    "ch03": ("3", "Text on the stage"),
}

NARRATION = {
    "ch00": [
        Beat("a1", "An explainer video is a sequence of small screens. Each screen appears on the words that explain it.",
             "Title of the video over an orange rule."),
        Beat("a2", "This demo uses sample data. It shows the blocks for charts, for diagrams, and for text that you can use in your own scenes.",
             "Subtitle, then three chips: charts, diagrams, text."),
    ],
    "ch01": [
        Beat("b1", "Here is a column chart. The numbers are sample data. Each column has its value on top, and the y axis is in percent.",
             "column_chart: four columns, values on top, y axis in percent."),
        Beat("b2", "A ranked bar chart works well for a few values that start at zero.",
             "ranked_bars: three models, the largest first."),
        Beat("b3", "When the values are near each other, use a dot plot. A bar on a cut axis gives a wrong proportion.",
             "dot_plot: three points between 60 and 75."),
        Beat("b4", "A line chart shows a trend. The dashed line marks a level.",
             "line_chart: two series, a dashed reference line at 50 percent."),
        Beat("b5", "Small multiples put two or more line charts on the same axis.",
             "small_multiples: three panels, one legend."),
    ],
    "ch02": [
        Beat("c1", "A pipeline shows the steps of a process. The orange arrow goes back: a loop.",
             "pipeline: input, step 1, step 2, output, with a loop from step 2 to step 1."),
        Beat("c2", "A flow diagram has boxes with names, and arrows between them.",
             "flow: start, model, result."),
        Beat("c3", "A loop on one box shows feedback. A dashed arrow shows a weaker relation.",
             "flow with a feedback loop under the model and a dashed arrow to a check box."),
        Beat("c4", "A table compares options. The scene shows one row at a time, on the words of the narration.",
             "compare_table: two options, three rows that appear one at a time."),
        Beat("c5", "A stack of layers, with a signal that goes through it from the bottom to the top.",
             "stack and sweep: a wave of light through nine layers."),
    ],
    "ch03": [
        Beat("d1", "A quotation keeps its source on the screen, and you can highlight one phrase when the voice reads it.",
             "quote: a sample quotation with its attribution."),
        Beat("d2", "Stat tiles show the key numbers of a part. Give them a note that says where the numbers come from.",
             "stat_tiles: three sample numbers."),
        Beat("d3", "Cards hold a note, a definition, or a limitation.",
             "cards: a definition and a limitation."),
        Beat("d4", "A statement at the center gives the conclusion of a part.",
             "statement: two lines at the center."),
        Beat("d5", "At the end, takeaways list the points of the video, and each one appears at its turn.",
             "takeaways: three points that appear one at a time."),
        Beat("d6", "The last screen shows where the content comes from.",
             "credits: source and data."),
    ],
}
