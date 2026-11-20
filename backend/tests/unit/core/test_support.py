from app.core.support import load_support_email, support_email


def test_support_email_comes_from_the_yaml_file(tmp_path):
    path = tmp_path / "support.yaml"
    path.write_text("support:\n  email: help@example.org\n")
    assert load_support_email(path) == "help@example.org"


def test_the_shipped_config_has_a_usable_email():
    assert "@" in support_email()
