import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="damo",
    version="0.0.2",
    author="SeongJae Park",
    author_email="sjpark@amazon.de",
    description="DAMON user-space tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/awslabs/damo",
    project_urls={
        "Bug Tracker": "https://github.com/awslabs/damo/issues",
        "DAMON": "https://damonitor.github.io",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: POSIX :: Linux",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    entry_points = {
        "console_scripts": ["damo=damo.damo:main"],
    },
    python_requires=">=3.6",
)
