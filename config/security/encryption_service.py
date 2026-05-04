#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Encryption service - AES-256-GCM Encryption for sensitive data
"""

import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# Master key derived from environment variable
MASTER_KEY = os.getenv('ENCRYPTION_KEY', 'TRADING_AI_BOT_MASTER_KEY_CHANGE_IN_PRODUCTION')
SALT = b'trading_ai_bot_salt_v1'

def _get_encryption_key():
    """Derive 32-byte key from master key using PBKDF2"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(MASTER_KEY.encode('utf-8'))

def encrypt_binance_keys(api_key, api_secret):
    """Encrypt Binance API keys using AES-256-GCM"""
    try:
        key = _get_encryption_key()
        aesgcm = AESGCM(key)
        
        # Generate random nonce for each encryption
        nonce_key = os.urandom(12)
        nonce_secret = os.urandom(12)
        
        # Encrypt
        encrypted_key = aesgcm.encrypt(nonce_key, api_key.encode('utf-8'), None)
        encrypted_secret = aesgcm.encrypt(nonce_secret, api_secret.encode('utf-8'), None)
        
        # Prepend nonce to ciphertext and encode as base64
        final_key = base64.b64encode(nonce_key + encrypted_key).decode('utf-8')
        final_secret = base64.b64encode(nonce_secret + encrypted_secret).decode('utf-8')
        
        return final_key, final_secret
    except Exception as e:
        raise Exception(f"Encryption failed: {str(e)}")

def decrypt_binance_keys(encrypted_key, encrypted_secret):
    """Decrypt Binance API keys"""
    try:
        key = _get_encryption_key()
        aesgcm = AESGCM(key)
        
        # Decode from base64
        data_key = base64.b64decode(encrypted_key)
        data_secret = base64.b64decode(encrypted_secret)
        
        # Extract nonce (first 12 bytes) and ciphertext
        nonce_key = data_key[:12]
        ciphertext_key = data_key[12:]
        nonce_secret = data_secret[:12]
        ciphertext_secret = data_secret[12:]
        
        # Decrypt
        decrypted_key = aesgcm.decrypt(nonce_key, ciphertext_key, None).decode('utf-8')
        decrypted_secret = aesgcm.decrypt(nonce_secret, ciphertext_secret, None).decode('utf-8')
        
        return decrypted_key, decrypted_secret
    except Exception as e:
        raise Exception(f"Decryption failed: {str(e)}")

def encrypt_text(text):
    """Encrypt generic text"""
    try:
        key = _get_encryption_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        encrypted = aesgcm.encrypt(nonce, text.encode('utf-8'), None)
        return base64.b64encode(nonce + encrypted).decode('utf-8')
    except Exception as e:
        raise Exception(f"Text encryption failed: {str(e)}")

def decrypt_text(encrypted_text):
    """Decrypt generic text"""
    try:
        key = _get_encryption_key()
        aesgcm = AESGCM(key)
        data = base64.b64decode(encrypted_text)
        nonce = data[:12]
        ciphertext = data[12:]
        decrypted = aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')
        return decrypted
    except Exception as e:
        raise Exception(f"Text decryption failed: {str(e)}")
