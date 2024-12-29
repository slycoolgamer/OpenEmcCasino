import os

# List of libraries to install
libraries = [
    "python-dotenv",
    "discord.py",
    "sqlite"
]

# Install each library using pip
for library in libraries:
    os.system(f"pip install {library}")

print("All libraries installed successfully!")
