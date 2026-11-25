"""Tests of the engine that need no network and no render: languages, speech rules,
subtitles, the layout verification, the blocks, the script and the configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
from manim import DOWN

from videogen import blocks, langs, paths, speech, subtitles, theme
from videogen import config as video_config
from videogen.narration import load_script
from videogen.tts import load_env

DEMO = Path(__file__).resolve().parent.parent / "examples" / "demo"
BLUE, ORANGE = theme.SERIES["blue"], theme.SERIES["orange"]


def test_number_formats():
    english, italian = langs.get("en"), langs.get("it")
    assert english.number(38.26) == "38.3"
    assert italian.number(38.26) == "38,3"
    assert english.percent(50) == "50\\%"
    assert italian.percent(38.26, 1) == "38,3\\%"


def test_unknown_language():
    with pytest.raises(KeyError):
        langs.get("xx")


def test_spoken_rules():
    assert speech.spoken("OpenAI made GPT-5.6", langs.get("it").spoken_rules) == "Open AI made GPT 5 punto 6"
    assert speech.spoken("GPT-5.6", []) == "GPT-5.6"
    assert speech.spoken("a-b", [(r"-", " ")]) == "a b"


def test_subtitles_follow_the_punctuation_and_the_pauses():
    words = [(0.0, 0.4, "A"), (0.45, 0.3, "line"), (0.8, 0.4, "of"), (1.25, 0.5, "text,"), (2.0, 0.4, "Then"), (2.45, 0.5, "more.")]
    cues = subtitles.group_cues(words)
    assert [text for _start, _end, text in cues] == ["A line of text,", "Then more."]
    text = subtitles.srt_text(cues, 10.0)   # the first line stops 0.05 s before the second one
    assert text == "1\n00:00:00,000 --> 00:00:01,950\nA line of text,\n\n2\n00:00:02,000 --> 00:00:03,200\nThen more.\n"


def test_subtitles_cut_long_lines():
    words = [(index * 0.5, 0.4, f"word{index}") for index in range(40)]
    cues = subtitles.group_cues(words)
    assert len(cues) > 1
    assert all(len(text) <= 54 + 9 for _start, _end, text in cues)   # 54 + one word
    assert " ".join(text for _s, _e, text in cues) == " ".join(f"word{index}" for index in range(40))


def test_subtitles_do_not_end_with_a_function_word():
    words = [(index * 0.4, 0.3, "word") for index in range(9)] + [(3.6, 0.3, "of"), (4.0, 0.4, "Rome")]
    cues = subtitles.group_cues(words, function_words=frozenset({"of"}))
    assert all(not text.endswith(" of") for _s, _e, text in cues)


def test_layout_verification():
    first = theme.T("first line").move_to([0, 0, 0])
    second = theme.T("second line").move_to([0, 0, 0])
    assert [issue.kind for issue in theme.layout_issues([first, second])] == ["overlap"]
    assert theme.layout_issues([first, second])[0].describe() == 'overlap: "first line" on "second line"'
    corner = theme.T("corner").move_to([7.4, 0, 0])
    assert [issue.kind for issue in theme.layout_issues([corner])] == ["out-of-frame"]
    apart = theme.T("apart").next_to(first, DOWN, buff=1.0)
    assert theme.layout_issues([first, apart]) == []
    faded = theme.T("faded line").move_to([0, 0, 0]).set_opacity(0.1)
    assert theme.layout_issues([first, faded]) == []
    box = theme.LabeledBox("in a box", BLUE).move_to([0, 0, 0])
    assert theme.layout_issues([box]) == []   # the text of a box is one line


def test_every_block_builds_a_clean_screen():
    diagram = blocks.flow(
        [("a", "A", BLUE, -4, 0), ("b", ["B", "a note"], ORANGE, 2, 0), ("c", "C", BLUE, 2, -2.4)],
        edges=[("a", "b"), ("b", "c", theme.INK["secondary"], "dashed")], loops=[("b", "above", theme.BRIGHT["orange"])],
    )
    chart = blocks.column_chart(["A", "B"], [1, 2], (0, 3), y_ticks=[0, 3], title="Columns", legend_entries=True, note="Sample data.")
    quotation = blocks.quote(["a {{b}} c"], "who")
    built = {
        "column_chart": chart.everything(),
        "ranked_bars": blocks.ranked_bars([("x", None, 2, BLUE), ("y", "small", 1, ORANGE)], (0, 3), x_ticks=[0, 3], title="Bars").everything(),
        "dot_plot": blocks.dot_plot([("x", 2, BLUE)], (1, 3), x_ticks=[1, 2, 3], title="Points", legend_entries=True).everything(),
        "line_chart": blocks.line_chart([("a", BLUE, [(0, 0), (1, 1)])], (0, 2), (0, 1), reference=(0.5, "level")).everything(),
        "small_multiples": blocks.small_multiples([("p", [("a", BLUE, [(0, 0), (1, 1)])])], (0, 2), (0, 1), x_label="steps", note="Sample data.").everything(),
        "quote": quotation.everything(),
        "takeaways": blocks.takeaways([("t", "d", theme.BRIGHT["green"]), ("t2", "d2", theme.BRIGHT["orange"])]).rows,
        "cards": blocks.cards([("h", "one line", theme.BRIGHT["violet"]), ("h2", ["two", "lines"], theme.BRIGHT["orange"])], [(-3.5, 0), (3.5, 0)]),
        "flow": diagram.everything(),
        "pipeline": blocks.pipeline([("one", BLUE), ("two", BLUE, "a note")], loop=(1, 0, "again")).everything(),
        "stat_tiles": blocks.stat_tiles([("42", "things")], [(0, 0)]),
        "credits": blocks.credits("Title", [("Source", "one line"), ("Data", ["two", "lines"])]),
        "statement": blocks.statement(["One line", "Two lines"]),
        "side_brace": blocks.side_brace(1.0, -0.5, 0.5, "label"),
    }
    table = blocks.compare_table([("A", "fixed"), ("B", "flexible")], ("Blocks", "Parameters"))
    built["compare_table"] = theme.VGroup(table.rules, table.headers, table.subheaders, table.labels, table.row(0, ["22", "22"]))
    for name, mobject in built.items():
        assert mobject.width > 0 and mobject.height > 0, name
        assert theme.layout_issues([mobject]) == [], name
    assert len(diagram.arrows) == 2 and list(diagram.loops) == ["b"]
    assert len(chart.marks) == 2 and len(chart.labels[0]) == 2
    assert quotation.part(0, 1).width > 0


def test_parts_of_the_blocks():
    diagram = blocks.flow([("a", "A", BLUE, -4, 0), ("b", "B", BLUE, 4, 0)], edges=[("a", "b")], loops=[("a", "right", ORANGE)])
    assert set(diagram.boxes) == {"a", "b"} and list(diagram.loops) == ["a"]
    quote = blocks.quote(["a {{b}} c"])
    assert quote.part(0, 1).width < quote.line(0).width
    table = blocks.compare_table([("A", None), ("B", "sub")], ("one", "two"))
    assert len(table.row(1, ["x", "y"])) == 2 and len(table.rules) == 3   # a line above and below each row
    assert len(table.subheaders) == 1   # the column without a subtitle has no text "None"
    chart = blocks.column_chart(["A", "B"], [1, 2], (0, 3))
    assert chart.title is None and chart.legend is None and len(chart.shell()) == 2


def test_demo_project_loads():
    script = load_script(DEMO)
    assert script.order == ["ch00", "ch01", "ch02", "ch03"]
    assert script.beat_count == 18
    assert script.keys("ch00") == ["a1", "a2"]
    config = video_config.load(DEMO)
    assert config.language == "en" and config.resolved_voice == "en-US-AndrewNeural"
    assert config.out == "scene-blocks-tour"


def test_script_validation(tmp_path):
    (tmp_path / "narration.py").write_text(
        "from collections import namedtuple\nBeat = namedtuple('Beat', 'key text visual')\n"
        "SCENE_ORDER = ['ch01']\nCHAPTERS = {'ch01': ('1', 'One')}\n"
        "NARRATION = {'ch01': [Beat('a1', 'first', 'x'), Beat('a1', 'again', 'y')]}\n", encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="used two times"):
        load_script(tmp_path)
    (tmp_path / "narration.py").write_text("SCENE_ORDER = ['intro']\nCHAPTERS = {}\nNARRATION = {}\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="not valid"):
        load_script(tmp_path)


def test_configuration(tmp_path):
    (tmp_path / "video.toml").write_text('title = "T & T"\nlanguage = "it"\n', encoding="utf-8")
    config = video_config.load(tmp_path)
    assert config.resolved_voice == "it-IT-IsabellaNeural" and config.lang.decimal_separator == ","
    (tmp_path / "video.toml").write_text('title = "T"\nrate = "fast"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="rate"):
        video_config.load(tmp_path)
    assert video_config.slugify("Scene blocks: a tour!") == "scene-blocks-a-tour"
    assert theme.plain("100% of a_b & c").width > 0


def test_tools_folder(tmp_path, monkeypatch):
    monkeypatch.delenv("AIVIDEOGEN_TOOLS", raising=False)
    assert paths.tools_root() == paths.template_root() / ".tools"
    assert paths.venv_bin() == paths.template_root() / ".tools" / "venv" / "bin"
    assert paths.models_root() == paths.template_root() / ".tools" / "models"
    monkeypatch.setenv("AIVIDEOGEN_TOOLS", str(tmp_path / "elsewhere"))
    assert paths.tools_root() == tmp_path / "elsewhere"


def test_find_the_video_project(tmp_path, monkeypatch):
    project = tmp_path / "videos" / "demo"
    (project / "scenes").mkdir(parents=True)
    (project / "video.toml").write_text('title = "T"\n', encoding="utf-8")
    monkeypatch.delenv("VIDEO_ROOT", raising=False)
    monkeypatch.chdir(project / "scenes")
    assert paths.in_video() == project.resolve()          # the nearest parent with video.toml
    assert paths.in_video(tmp_path / "other") == (tmp_path / "other").resolve()
    monkeypatch.chdir(tmp_path)
    with pytest.raises(LookupError):
        paths.in_video()


def test_the_wrapper_starts_videogen():
    import subprocess

    wrapper = paths.template_root() / "tools" / "videogen"
    done = subprocess.run([str(wrapper), "--version"], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert done.stdout.startswith("videogen ")


def test_env_file(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text('# comment\nMY_KEY="abc def"\nexport OTHER=1\nNOT A LINE\n', encoding="utf-8")
    monkeypatch.setenv("OTHER", "already")
    assert load_env(path) == ["MY_KEY"]
    import os
    assert os.environ["MY_KEY"] == "abc def" and os.environ["OTHER"] == "already"


def test_new_project_from_the_templates(tmp_path):
    import subprocess
    import sys

    folder = tmp_path / "my-video"
    done = subprocess.run([sys.executable, "-m", "videogen.cli", "new", str(folder), "--language", "it", "--title", "Prova"], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert (folder / "video.toml").read_text(encoding="utf-8").count("it-IT") == 0   # the voice is the default of the language
    script = load_script(folder)
    assert script.order == ["ch00"] and script.beat_count == 2
    assert video_config.load(folder).resolved_voice == "it-IT-IsabellaNeural"
    assert (folder / "scenes" / "ch00_intro.py").is_file()


def test_script_without_a_quality_uses_the_time_of_the_final_render(tmp_path):
    """Without `--quality`, the command read the timing of the voice in place of a time line, and
    stopped with an error."""
    from videogen import cli

    (tmp_path / "video.toml").write_text('title = "T"\nlanguage = "en"\n', encoding="utf-8")
    (tmp_path / "narration.py").write_text(
        "from collections import namedtuple\nBeat = namedtuple('Beat', 'key text visual')\nSCENE_ORDER = ['ch00']\n"
        "CHAPTERS = {'ch00': ('', '')}\n"
        "NARRATION = {'ch00': [Beat('a1', 'One.', 'a line'), Beat('a2', 'Two.', 'a line')]}\n",
        encoding="utf-8",
    )
    timing = tmp_path / "build" / "timing"
    (timing / "h").mkdir(parents=True)
    (timing / "ch00.json").write_text('{"beats": {"a1": {"dur": 1.5}, "a2": {"dur": 2.5}}}', encoding="utf-8")
    (timing / "h" / "ch00.json").write_text('{"beats": [["a1", 0.5, 2.0], ["a2", 2.0, 4.5]], "total": 4.5}',
                                            encoding="utf-8")
    cli.cmd_script(cli.build_parser().parse_args(["script", "--root", str(tmp_path)]))
    text = (tmp_path / "script.md").read_text(encoding="utf-8")
    assert "| a1 | 00:00.50 |" in text and "| a2 | 00:02.00 |" in text


def test_the_sheets_of_the_film_need_the_film_of_the_last_render(tmp_path):
    """The frames come from the film. A film at another quality, of another narration, or older
    than a scene would show an old video."""
    import json
    import os

    from videogen import cli

    (tmp_path / "video.toml").write_text('title = "T"\nlanguage = "en"\n', encoding="utf-8")
    (tmp_path / "narration.py").write_text(
        "from collections import namedtuple\nBeat = namedtuple('Beat', 'key text visual')\nSCENE_ORDER = ['ch00']\n"
        "CHAPTERS = {'ch00': ('', '')}\nNARRATION = {'ch00': [Beat('a1', 'One.', 'a line')]}\n", encoding="utf-8",
    )
    config, script = video_config.load(tmp_path), load_script(tmp_path)
    with pytest.raises(RuntimeError, match="No film at quality 'h'"):
        cli.assembled_film(config, "h", script)
    out = tmp_path / "out"
    out.mkdir()
    film = out / f"{config.out}_1080p.mp4"
    film.write_bytes(b"")
    chapters = [{"start": 0.0, "title": ""}]
    (out / "film.json").write_text(json.dumps({"file": film.name, "chapters": chapters * 2}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="not a film of this narration"):
        cli.assembled_film(config, "h", script)
    (out / "film.json").write_text(json.dumps({"file": film.name, "chapters": chapters}), encoding="utf-8")
    timeline = tmp_path / "build" / "timing" / "h"
    timeline.mkdir(parents=True)
    (timeline / "ch00.json").write_text('{"beats": [["a1", 0.5, 4.0]]}', encoding="utf-8")
    os.utime(film, (1, 1))
    with pytest.raises(RuntimeError, match="older than the video of ch00"):
        cli.assembled_film(config, "h", script)
    os.utime(timeline / "ch00.json", (1, 1))
    assert cli.assembled_film(config, "h", script) == (film, {"ch00": 0.0})
