
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import base64
import logging

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_ENCRYPTION_KEY").encode()

def add_pkcs7_padding(data, block_size=16):
    
    padding_length = block_size - (len(data) % block_size)
    padding = bytes([padding_length] * padding_length)
    return data + padding

def encrypt_data(data):
    salt = os.urandom(8)  

    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=48,  
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    derived_key = kdf.derive(SECRET_KEY)
    key = derived_key[:32]  # First 32 bytes key
    iv = derived_key[32:]    # Last 16 bytes  IV
    
    # Add PKCS7 padding to the data
    padded_data = add_pkcs7_padding(data.encode())
    
    # Encrypt the data
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    
    # Combine "Salted__", salt, and encrypted data
    combined = b"Salted__" + salt + encrypted_data
    
    # Return as base64-encoded string
    return base64.b64encode(combined).decode()


def decrypt_data(encrypted_data):
    try:
        encrypted_data = base64.b64decode(encrypted_data.encode())
        
        if encrypted_data.startswith(b"Salted__"):
            salt = encrypted_data[8:16]
            # The actual encrypted data starts from byte 16
            encrypted_data = encrypted_data[16:]
            
            # Derive the key and IV using the salt
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives import hashes
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=48,  # 32 bytes for key + 16 bytes for IV
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            derived_key = kdf.derive(SECRET_KEY)
            key = derived_key[:32]  # First 32 bytes key
            iv = derived_key[32:]    # Last 16 bytes  IV
        else:
            iv = encrypted_data[:16]
            encrypted_data = encrypted_data[16:]
            key = SECRET_KEY

        # Decrypt the data
        cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
        
        # Remove padding (PKCS7)
        padding_length = decrypted_data[-1]
        decrypted_data = decrypted_data[:-padding_length]
        
        # Log the decrypted bytes
        logger.debug(f"Decrypted bytes: {decrypted_data}")
        
        # Decode to UTF-8
        return decrypted_data.decode('utf-8')
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise

