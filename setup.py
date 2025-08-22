from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="toronto-streetview-crawler",
    version="0.1.0",
    author="Alex",
    description="A tool to crawl Google Street View panoramas within Toronto's boundaries",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "toronto-open-data",
        "geopandas",
        "matplotlib",
        "shapely",
        "pyproj",
        "fiona",
        "streetlevel",
    ],
    entry_points={
        "console_scripts": [
            "toronto-boundary=toronto_streetview_crawler.load_boundary:main",
            "toronto-panorama=toronto_streetview_crawler.get_panorama:main",
            "toronto-crawl=toronto_streetview_crawler.crawl:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
