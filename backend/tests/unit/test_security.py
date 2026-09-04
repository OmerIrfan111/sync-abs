import pytest
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    encrypt_credential,
    decrypt_credential
)
from jose import jwt
from app.core.config import settings

def test_password_hashing():
    pwd = "superSecretPassword123!"
    hashed = get_password_hash(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrongPassword", hashed) is False

def test_jwt_token_generation_and_decoding():
    user_id = 42
    token = create_access_token(user_id)
    assert isinstance(token, str)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["sub"] == "42"
    assert "exp" in payload

def test_credential_encryption_and_decryption():
    secret_api_key = "ingram_secret_prod_key_9988776655"
    cipher = encrypt_credential(secret_api_key)
    assert cipher != secret_api_key
    decrypted = decrypt_credential(cipher)
    assert decrypted == secret_api_key

def test_credential_empty_cases():
    assert encrypt_credential("") == ""
    assert decrypt_credential("") == ""
    assert decrypt_credential("corrupted_cipher_data") == ""
