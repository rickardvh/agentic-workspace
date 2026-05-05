from sample_app import summarize_words, to_slug


def test_summarize_words_keeps_short_text():
    assert summarize_words("one two three", limit=5) == "one two three"


def test_to_slug_handles_simple_title():
    assert to_slug("Hello World") == "hello-world"


def test_to_slug_collapses_repeated_whitespace():
    assert to_slug("Hello   Wide   World") == "hello-wide-world"
