from metaedit.models import SpeakerMetadata


def test_convert_legacy_reviews_single_field():
    data = {
        "brand": "X",
        "model": "Y",
        "measurements": {"asr": {"origin": "ASR", "review": "https://example.com/r"}},
    }
    converted = SpeakerMetadata.convert_legacy_reviews(data)
    assert "review" not in converted["measurements"]["asr"]
    assert converted["measurements"]["asr"]["reviews"] == {"default": "https://example.com/r"}


def test_date_formatting_roundtrip():
    src = "20240131"
    as_input = SpeakerMetadata.format_date_for_input(src)
    assert as_input == "2024-01-31"
    back = SpeakerMetadata.format_date_for_python(as_input)
    assert back == src
