from app.core.markdown_plain_text import markdown_content_length, markdown_to_plain_text


def test_markdown_plain_text_strips_formatting_markers() -> None:
    assert markdown_to_plain_text("**bold** and _italic_") == "bold and italic"
    assert markdown_to_plain_text("[label](https://example.com)") == "label"
    assert markdown_to_plain_text("- one\n- two") == "one\ntwo"
    assert markdown_to_plain_text("> quoted") == "quoted"
    assert markdown_to_plain_text("`code`") == "code"


def test_markdown_content_length_ignores_markers() -> None:
    assert markdown_content_length("**hello**") == 5
    assert markdown_content_length("hello") == 5
    assert markdown_content_length("x" * 500) == 500
    assert markdown_content_length("**" + ("x" * 500) + "**") == 500
