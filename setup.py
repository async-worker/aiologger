from setuptools import setup, find_packages


VERSION = '0.0.1'

setup(
    name='aiologger',
    version=VERSION,
    packages=find_packages(exclude=['*test*']),
    url='https://github.com/diogommartins/aiologger',
    author='Diogo Magalhães Martins',
    author_email='magalhaesmartins@icloud.com',
    keywords='logging json log output',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3.6'
    ]
)
