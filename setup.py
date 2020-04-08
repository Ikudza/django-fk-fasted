from setuptools import setup

setup(
    name='django_fk_fasted',
    version='0.0.1',
    py_modules=['django_fk_fasted'],
    long_description=open('README.md').read(),
    python_requires='>=3.7',
    install_requires=[
        'django>=2.2',
        'django_redis>=4.10'
    ],
)
