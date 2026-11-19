import pytest

from app.guardrails.preprocess import InputRejectedError, preprocess


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_grd_01_empty_input_is_rejected(text):
    with pytest.raises(InputRejectedError):
        preprocess(text)


def test_grd_01_input_over_1000_characters_is_rejected():
    with pytest.raises(InputRejectedError):
        preprocess("a" * 1001)


def test_exactly_1000_characters_is_fine():
    assert len(preprocess("a" * 1000).text) == 1000


def test_grd_02_control_characters_removed_and_unicode_normalised():
    result = preprocess("Spend\x00 by\x07 vendor​ ｆｏｒ Ｚｅｎｉｔｈ")
    assert result.text == "Spend by vendor for Zenith"


def test_whitespace_is_collapsed_but_newlines_kept_as_spaces():
    assert preprocess("  open\n\n POs   please ").text == "open POs please"


def test_grd_06_secrets_typed_into_chat_are_masked_and_flagged():
    result = preprocess("my key is sk-proj-abcdefghijklmnopqrstuvwxyz123456 show spend")
    assert "sk-proj" not in result.text
    assert "[SECRET]" in result.text
    assert result.masked_kinds == {"secret"}


def test_personal_data_typed_into_chat_is_masked():
    result = preprocess("email ravi@example.com or call +91 98765 43210")
    assert result.text == "email [EMAIL] or call [PHONE]"
    assert result.masked_kinds == {"email", "phone"}
