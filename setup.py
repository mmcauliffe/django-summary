from setuptools import setup, find_packages

packages = find_packages()
template_patterns = [
    'templates/*.html',
    'templates/*/*.html',
    'templates/*/*/*.html',
    ]

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
    packages=packages,
    package_data=dict( (package_name, template_patterns)
                   for package_name in packages ),
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
