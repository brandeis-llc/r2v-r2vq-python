import setuptools

with open('requirements.txt') as requirements:
    requires = requirements.readlines()

setuptools.setup(
    name="r2vq",
    version='0.1.0',
    author="Brandeis-LLC",
    description="r2vq-python package provides common operations over R2VQ dataset.",
    install_requires=requires,
    python_requires='>=3.7',
    packages=['r2vq'],
    package_data={
        'r2vq': ['res/*'],
    },
    entry_points={},
)
