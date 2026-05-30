from cryptography.fernet import Fernet

key = Fernet.generate_key()
print(f"生成的 ENCRYPTION_KEY:")
print(key.decode())
