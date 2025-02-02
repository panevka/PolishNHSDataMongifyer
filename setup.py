from setuptools import setup, find_packages

setup(
    name="PolishNHSDataMongifyer",
    version="0.1",
    description="Python tool for creating mongo-compatible json files, that contain polish NHS data of chosen services", 
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="panevka",
    author_email="97028404+panevka@users.noreply.github.com",
    url="https://github.com/panevka/PolishNHSDataMongifyer",
    packages=find_packages(),
    classifiers=[ 
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
    "annotated-types>=0.7.0", 
    "certifi>=2024.12.14", 
    "charset-normalizer>=3.4.1", 
    "docopt>=0.6.2", 
    "idna>=3.10", 
    "pipreqs>=0.4.13", 
    "pydantic>=2.10.5", 
    "pydantic_core>=2.27.2", 
    "python-dotenv>=1.0.1", 
    "requests>=2.32.3", 
    "setuptools>=75.8.0", 
    "typing_extensions>=4.12.2", 
    "urllib3>=2.3.0", 
    "yarg>=0.1.10"
    ],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "run=src.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
