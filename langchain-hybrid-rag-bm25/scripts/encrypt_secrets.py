import os
import sys
from cryptography.fernet import Fernet

def generate_key():
    key = Fernet.generate_key()
    print("\n[SUCCESS] New Master Key Generated!")
    print("--------------------------------------------------")
    print(key.decode())
    print("--------------------------------------------------")
    print("WARNING: Save this key securely. You must set it as the MASTER_KEY environment variable.")

def encrypt_value(key: str, value: str):
    try:
        f = Fernet(key.encode())
        encrypted = f.encrypt(value.encode())
        print(f"\n[SUCCESS] Encrypted Value:")
        print(f"ENC:{encrypted.decode()}")
        print("\nYou can now copy and paste this into your .env file.")
    except Exception as e:
        print(f"[ERROR] Failed to encrypt: {e}")

if __name__ == "__main__":
    print("Secret Encryption Utility")
    print("1. Generate a new MASTER_KEY")
    print("2. Encrypt a secret (e.g. Postgres Password, API Key)")
    
    try:
        choice = input("\nEnter choice (1 or 2): ").strip()
        if choice == "1":
            generate_key()
        elif choice == "2":
            key = input("Enter your MASTER_KEY: ").strip()
            value = input("Enter the plaintext secret to encrypt: ").strip()
            encrypt_value(key, value)
        else:
            print("Invalid choice.")
    except KeyboardInterrupt:
        sys.exit(0)
