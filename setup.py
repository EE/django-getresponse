from setuptools import find_packages, setup


setup(
    name='django-getresponse',
    version='0.2.0',
    packages=find_packages(),
    install_requires=[
        'django',
        'requests',
    ],
)
