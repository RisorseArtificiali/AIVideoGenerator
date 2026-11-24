"""Languages: the voices, the number format and the interface strings of one narration
language. Add a language with an entry in LANGS."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Language:
    code: str
    name: str
    # Speech engine id -> voices for this language. The first voice is the default.
    voices: dict[str, tuple[str, ...]]
    # Short words that a line of the subtitles must not end with.
    function_words: frozenset[str]
    decimal_separator: str
    # (regular expression, replacement): how the voice reads some names. The script keeps
    # the normal spelling; only the voice gets the changed text.
    spoken_rules: tuple[tuple[str, str], ...] = ()
    text: dict[str, str] = field(default_factory=dict)

    def number(self, value: float, decimals: int = 1) -> str:
        """A number in the format of the language: `38.3` or `38,3`."""
        return f"{value:.{decimals}f}".replace(".", self.decimal_separator)

    def percent(self, value: float, decimals: int = 0) -> str:
        """A percentage for LaTeX text: for example `38\\%` or `38,3\\%`."""
        return self.number(value, decimals) + "\\%"


ENGLISH_TEXT = {
    "opening": "Opening",
    "script_title": "Script",
    "duration": "Duration",
    "voice": "Voice",
    "speed": "Speed",
    "chapters": "chapters",
    "beats": "beats",
    "id": "ID",
    "start": "Start",
    "narration": "Text that the voice reads",
    "on_screen": "On screen",
    "note": (
        "Each row of the table is one audio clip. The animation of the scene follows that clip, "
        "and the words in it."
    ),
    "test_sentence": "One, two, three.",
    "beat_1": "Here is the first sentence that the voice says.",
    "visual_1": "What is on the screen during this beat.",
    "beat_2": "Here is the second sentence: the title of the video appears.",
    "visual_2": "Title of the video.",
}

ITALIAN_TEXT = {
    "opening": "Apertura",
    "script_title": "Copione",
    "duration": "Durata",
    "voice": "Voce",
    "speed": "Velocità",
    "chapters": "capitoli",
    "beats": "battute",
    "id": "ID",
    "start": "Inizio",
    "narration": "Testo letto dalla voce",
    "on_screen": "Sullo schermo",
    "note": (
        "Ogni riga della tabella è un clip audio. L'animazione della scena segue quel clip, "
        "e le parole al suo interno."
    ),
    "test_sentence": "Uno, due, tre.",
    "beat_1": "Qui va la prima frase che la voce legge.",
    "visual_1": "Cosa compare sullo schermo in questa battuta.",
    "beat_2": "Qui va la seconda frase: appare il titolo del video.",
    "visual_2": "Titolo del video.",
}

LANGS: dict[str, Language] = {
    "en": Language(
        code="en",
        name="English",
        voices={
            "edge-tts": ("en-US-AndrewNeural", "en-US-AvaNeural", "en-GB-RyanNeural", "en-GB-SoniaNeural"),
        },
        function_words=frozenset(
            """a an the of to in on at for with by from and or but so as is are was were be been that this
            these those it its into than then not no also which who if we you they he she i your our their
            his her my about over after before more most can will would could does do has have""".split()
        ),
        decimal_separator=".",
        text=ENGLISH_TEXT,
    ),
    "it": Language(
        code="it",
        name="Italiano",
        voices={
            "edge-tts": ("it-IT-IsabellaNeural", "it-IT-ElsaNeural", "it-IT-DiegoNeural"),
        },
        function_words=frozenset(
            """e o ed a ad al allo ai agli alla alle di del dello dei degli della delle che chi cui il lo
            la i gli le un uno una per con su in nel nella sul dalla dal dalle dai ma né se come tra fra
            anche non più meno""".split()
        ),
        decimal_separator=",",
        spoken_rules=(
            (r"OpenAI", "Open AI"),
            (r"GPT-(\d)\.(\d+)", r"GPT \1 punto \2"),
            (r"GPT-(\d)", r"GPT \1"),
        ),
        text=ITALIAN_TEXT,
    ),
}


def get(code: str) -> Language:
    try:
        return LANGS[code]
    except KeyError:
        raise KeyError(f"Language '{code}' is not defined. Available: {', '.join(LANGS)}") from None
