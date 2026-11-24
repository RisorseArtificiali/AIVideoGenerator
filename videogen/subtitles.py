"""Subtitles: the timed words of the voice-over, grouped in short lines."""

from __future__ import annotations


def letters(word: str) -> str:
    return "".join(character for character in word.lower() if character.isalnum())


def ends_clause(word: str) -> bool:
    return len(word) > 1 and word[-1] in ".,:;?!»”)"


def group_cues(words, function_words=frozenset(), pause: float = 0.5, soft: int = 36, hard: int = 54) -> list[tuple[float, float, str]]:
    """Group timed words in subtitle lines. A line ends at a pause, after the punctuation of
    a sentence, or when it is long. A line does not end with (or start with) a short
    function word. `words` are (start in seconds, duration in seconds, word)."""
    cues, line, line_start, last_end = [], [], None, None
    for start, duration, word in words:
        paused = last_end is not None and start - last_end > pause
        joined = " ".join(line)
        too_long = bool(line) and (
            len(joined) > hard or (len(joined) > soft and letters(line[-1]) not in function_words and letters(word) not in function_words)
        )
        if line and (paused or too_long):
            cues.append((line_start, last_end + 0.25, joined))
            line, line_start = [], None
        if line_start is None:
            line_start = start
        line.append(word)
        last_end = start + duration
        if ends_clause(word) and len(" ".join(line)) >= 12:
            cues.append((line_start, last_end + 0.3, " ".join(line)))
            line, line_start, last_end = [], None, None
    if line:
        cues.append((line_start, last_end + 0.25, " ".join(line)))
    return cues


def srt_time(seconds: float) -> str:
    hours, rest = divmod(max(0.0, seconds), 3600)
    minutes, rest = divmod(rest, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{rest:06.3f}".replace(".", ",")


def srt_text(cues, limit: float) -> str:
    """The text of an .srt file. Each cue is at least 0.9 seconds and stops before the next."""
    out = []
    for index, (start, end, text) in enumerate(cues, start=1):
        next_start = cues[index][0] - 0.05 if index < len(cues) else limit
        out.append(f"{index}\n{srt_time(start)} --> {srt_time(min(max(end, start + 0.9), next_start))}\n{text}\n")
    return "\n".join(out)   # each item ends with a line break: the join makes the empty line between cues
