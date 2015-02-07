from setuptools import setup, find_packages

setup(
    name = "windfarm",
    version = "0.1",
    author = "snare",
    author_email = "snare@ho.ax",
    description = ("A stupid twitter bot"),
    license = "Buy snare a beer",
    keywords = "stupid twitter bot",
    url = "https://github.com/snare/windfarm",
    packages=find_packages(),
    package_data = {'windfarm': ['config/*']},
    install_package_data = True,
    install_requires = ['scruffy', 'python-twitter'],
    entry_points = {
        'console_scripts': ['windfarm = windfarm:main']
    },
    zip_safe = False,
    dependency_links = ["https://github.com/snare/scruffy/tarball/v0.3#egg=scruffy"]
)
