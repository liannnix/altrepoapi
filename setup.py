import codecs
from setuptools import setup, find_packages
from altrepo_api.version import __version__


with codecs.open("README.md", encoding="utf-8") as f:
    README = f.read()

with codecs.open("CHANGELOG.md", encoding="utf-8") as f:
    CHANGELOG = f.read()

requirements = None
with open("requirements.txt", "r") as f:
    requirements = [line.rstrip() for line in f.readlines() if not line.startswith("-")]

setup(
    name="altrepo-api",
    version=__version__,
    author="Danil Shein",
    author_email="dshein@altlinux.org",
    python_requires=">=3.7",
    packages=find_packages(),
    url="https://git.altlinux.org/gears/a/altrepo-api.git",
    license="GNU AGPLv3",
    description="ALTRepo REST API",
    include_package_data=True,
    long_description="\n".join((README, CHANGELOG)),
    long_description_content_type="text/markdown",
    zip_safe=False,
    install_requires=requirements,
    keywords="altrepo altrepo_api",
    scripts=["bin/altrepo-api"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Flask",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
