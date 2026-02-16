from setuptools import setup, find_packages

# Requirements file for production to install_requires
with open('requirements/prod.txt', encoding='utf-8') as f:
    REQUIREMENTS = f.read().splitlines()

setup(
    name="notifee",
    version="1.0.0",
    description="Non-blocking HTTP notification client",
    package_dir={"": "src"},
    package_data={'': ['py.typed']},
    packages=find_packages(where="src"),
    python_requires=">=3.10",
    install_requires=REQUIREMENTS,
)
