from backend.app.core.passwords import hash_password, verify_password


def test_password_hashing_and_verification() -> None:
    password = "correct horse battery staple"
    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert password not in first_hash
    assert first_hash != second_hash
    assert verify_password(password, first_hash)
    assert verify_password(password, second_hash)
    assert not verify_password("wrong password", first_hash)
    assert not verify_password(password, "not-an-argon2-hash")
