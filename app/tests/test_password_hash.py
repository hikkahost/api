import pytest

from app.utils.password_hash import validate_password_hash

_DEFAULT_PASSWORD = "$2b$12$nr213f0pJnQuCAdLnRTMeODqoniH1YH.Aqp6x2a9Wam01FtLdCB7O"


def test_validate_password_hash_accepts_default():
    assert validate_password_hash(_DEFAULT_PASSWORD) == _DEFAULT_PASSWORD


def test_validate_password_hash_accepts_variants():
    suffix = "nr213f0pJnQuCAdLnRTMeODqoniH1YH.Aqp6x2a9Wam01FtLdCB7O"
    assert validate_password_hash(f"$2a$04${suffix}")
    assert validate_password_hash(f"$2y$31${suffix}")


@pytest.mark.parametrize(
    "value",
    [
        "",
        "plaintext",
        "hash",
        "$2b$12$short",
        "$2b$99$nr213f0pJnQuCAdLnRTMeODqoniH1YH.Aqp6x2a9Wam01FtLdCB7O",
        "$2z$12$nr213f0pJnQuCAdLnRTMeODqoniH1YH.Aqp6x2a9Wam01FtLdCB7O",
        "$2b$12$invalid+charsODqoniH1YH.Aqp6x2a9Wam01FtLdCB7O",
    ],
)
def test_validate_password_hash_rejects_invalid(value):
    with pytest.raises(
        ValueError, match="Invalid password hash|Password hash required"
    ):
        validate_password_hash(value)
