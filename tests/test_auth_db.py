from app.database import register_user, verify_user


def test_register_and_verify():
    user_id = register_user("Ade", "correct-password")

    assert user_id is not None
    assert verify_user("ade", "correct-password") == user_id


def test_wrong_password_rejected():
    register_user("tolu", "correct-password")

    assert verify_user("tolu", "wrong-password") is None


def test_duplicate_username_rejected():
    assert register_user("chidi", "password-one") is not None
    assert register_user("CHIDI", "password-two") is None


def test_unknown_user_rejected():
    assert verify_user("nobody", "whatever") is None
