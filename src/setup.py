from setuptools import setup, find_packages

setup(
    name="mdllama",
    version="20250717.2",
    description="A command-line interface for Ollama API",
    author="QinCai-rui",
    packages=find_packages(),
    install_requires=[
        "requests",
        "rich",
        "colorama"
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "mdllama=mdllama.main:main"
        ]
    },
)



