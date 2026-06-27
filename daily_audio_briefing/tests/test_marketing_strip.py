"""Subscribe/newsletter footers (marketing) must never reach the audio briefing."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from source_fetcher import (
    _strip_subscribe_boilerplate,
    format_items_for_audio,
    FetchedItem,
    SourceType,
)


def test_strips_substack_footer_keeps_news():
    text = (
        "A new open-weights model shipped today and tops several benchmarks. "
        "Thanks for reading The Innermost Loop! Subscribe for free to receive new posts and support my work. "
        "Regulators are still deciding how to respond."
    )
    out = _strip_subscribe_boilerplate(text)
    assert "Thanks for reading" not in out
    assert "Subscribe for free" not in out
    assert "support my work" not in out
    assert "new open-weights model shipped" in out          # real news kept
    assert "Regulators are still deciding" in out


def test_format_items_for_audio_drops_footer():
    item = FetchedItem(
        title="Welcome to June 27, 2026",
        url="",
        content="",
        source_name="The Innermost Loop",
        source_type=SourceType.RSS,
        summary=("A real update about export-control policy. "
                 "Thanks for reading The Innermost Loop! Subscribe for free to receive new posts and support my work."),
    )
    out = format_items_for_audio([item])
    assert "Subscribe for free" not in out
    assert "Thanks for reading" not in out
    assert "export-control policy" in out


def test_does_not_strip_editorial_subscribe_mentions():
    """The footer regex must not eat legitimate editorial sentences."""
    keep = [
        "Developers can subscribe for free during the open beta to test the API.",
        "Thanks for reading between the lines, the real message is about export controls.",
        "The platform lets academics upgrade to a paid tier for GPU access.",
        "Users were urged to share this post widely to raise awareness.",
    ]
    for sentence in keep:
        assert _strip_subscribe_boilerplate(sentence) == sentence, f"wrongly stripped: {sentence!r}"


def test_strips_repeated_footers():
    """The footer leaked multiple times in one summary — every copy must go, news kept."""
    text = ("Policy update one. Thanks for reading The Innermost Loop! Subscribe for free to "
            "receive new posts and support my work. Policy update two. Thanks for reading The "
            "Innermost Loop! Subscribe for free to receive new posts and support my work. The end.")
    out = _strip_subscribe_boilerplate(text)
    assert "Subscribe for free" not in out and "support my work" not in out
    assert "Policy update one" in out and "Policy update two" in out and "The end" in out
