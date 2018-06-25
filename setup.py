from setuptools import setup, find_packages


VERSION = '0.1.0'
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
        'Framework :: AsyncIO',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Information Technology',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: System :: Logging'
    ]
)
