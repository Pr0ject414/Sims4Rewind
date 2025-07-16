import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

def generate_keys(private_key_path="private_key.pem", public_key_path="public_key.pem"):
    """
    Generates an RSA private and public key pair and saves them to PEM files.
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()

    # Save private key
    with open(private_key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption() # For simplicity, no encryption. In production, use encryption.
        ))
    print(f"Private key saved to {private_key_path}")

    # Save public key
    with open(public_key_path, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    print(f"Public key saved to {public_key_path}")

def sign_file(file_path, private_key_path, signature_path):
    """
    Signs a file using the provided private key and saves the signature to a file.
    """
    with open(private_key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None, # No password for simplicity
            backend=default_backend()
        )

    with open(file_path, "rb") as f:
        file_content = f.read()
    
    signature = private_key.sign(
        file_content,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

    with open(signature_path, "wb") as f:
        f.write(signature)
    print(f"Signature for {file_path} saved to {signature_path}")

def verify_signature(file_path, signature_path, public_key_path):
    """
    Verifies a file's signature using the provided public key.
    Returns True if the signature is valid, False otherwise.
    """
    with open(public_key_path, "rb") as key_file:
        public_key = serialization.load_pem_public_key(
            key_file.read(),
            backend=default_backend()
        )

    with open(file_path, "rb") as f:
        file_content = f.read()

    with open(signature_path, "rb") as f:
        signature = f.read()

    try:
        public_key.verify(
            signature,
            file_content,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        print(f"Signature for {file_path} is VALID.")
        return True
    except Exception as e:
        print(f"Signature for {file_path} is INVALID: {e}")
        return False

if __name__ == "__main__":
    # Example Usage:
    # 1. Generate keys
    generate_keys("my_private_key.pem", "my_public_key.pem")

    # 2. Create a dummy file to sign
    dummy_file_path = "dummy_update.zip"
    with open(dummy_file_path, "w") as f:
        f.write("This is a dummy update file content.")

    # 3. Sign the dummy file
    sign_file(dummy_file_path, "my_private_key.pem", "dummy_update.zip.sig")

    # 4. Verify the signature
    verify_signature(dummy_file_path, "dummy_update.zip.sig", "my_public_key.pem")

    # 5. Tamper with the file and try to verify again
    with open(dummy_file_path, "a") as f:
        f.write("tampered content")
    verify_signature(dummy_file_path, "dummy_update.zip.sig", "my_public_key.pem")

    # Clean up dummy files
    os.remove("my_private_key.pem")
    os.remove("my_public_key.pem")
    os.remove(dummy_file_path)
    os.remove("dummy_update.zip.sig")
