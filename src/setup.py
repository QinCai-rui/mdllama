from setuptools import setup

setup(
    name="mdllama",
    version="2.1.0",
    description="A command-line interface for Ollama API",
    author="QinCai-rui",
    py_modules=["mdllama"],
    install_requires=[
        "requests",
        "rich"
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "mdllama=mdllama:main"
        ]
    },
)
