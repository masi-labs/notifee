from setuptools import setup, find_packages

setup(
    name="notifee",
    version="0.1.0",
    description="Non-blocking HTTP notification client",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.10",
    install_requires=[
        "requests>=2.28.0",
    ],
)
