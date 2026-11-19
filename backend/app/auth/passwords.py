from __future__ import annotations

import bcrypt


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


# A real hash, so checks against unknown emails take as long as checks against known ones.
DUMMY_HASH = "$2b$12$GSOBsJpJYCGB0KYU/yNUQezUNPI6I9E2paN4zJ7kKwvCxxsaLNaiO"
