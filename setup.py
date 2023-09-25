import setuptools

setuptools.setup(
    name="cfsroutes",
    version="0.0.1a0",
    author="mjvk",
    author_email="",
    description="Domain specific delivery route creation.",
    long_description="",
    package_dir={"": "src"},
    packages=["cfsroutes"],
    install_requires=["requests", "ortools", "numpy"],
    python_requires=">=3.8",
    classifiers=["Programming Language :: Python :: 3", "Operating System :: OS Independent"],
    entry_points={"console_scripts": ["cfsroutes=cfsroutes.routes:cli"]},
)