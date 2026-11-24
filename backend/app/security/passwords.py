from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()
DUMMY_HASH = password_hasher.hash('not-a-real-password-for-timing')


def hash_password(password):
    return password_hasher.hash(password)


def verify_password(password, hashed):
    return password_hasher.verify(password, hashed)
