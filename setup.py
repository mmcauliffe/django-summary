from setuptools import setup, find_packages


setup(
    name='django-summary',
    version='0.1.0',
    description='Django package for summarizing informations from models.',
    long_description='',
    keywords='django, summaries',
    author='Michael McAuliffe',
    author_email='michael.e.mcauliffe@gmail.com',
    url='https://github.com/mmcauliffe/django-summary',
    license='BSD',
    packages=find_packages(),
    zip_safe=False,
    install_requires=['Django',],
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Framework :: Django",
        "Environment :: Web Environment",
    ]
)