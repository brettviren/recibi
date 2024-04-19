import setuptools

ver_globals = {}
with open("recibi/version.py") as fp:
    exec(fp.read(), ver_globals)
version = ver_globals["version"]

setuptools.setup(
    name="recibi",
    version=version,
    author="Brett Viren",
    author_email="brett.viren@gmail.com",
    description="Reference Citation Bibliography",
    url="https://brettviren.github.io/recibi",
    packages=setuptools.find_packages(),
    python_requires='>=3.6',
    install_requires=[
        "click",
        "pybtex",
    ],
    entry_points = dict(
        console_scripts = [
            'recibi = recibi.__main__:main',
        ]
    ),
)
