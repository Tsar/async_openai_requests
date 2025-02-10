from setuptools import find_packages
from distutils.core import setup
import os

# User-friendly description from README.md
current_directory = os.path.dirname(os.path.abspath(__file__))
try:
    with open(os.path.join(current_directory, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
except Exception:
    long_description = ''

setup(
	name='async_openai_requests',
	packages=find_packages('.'),
	version='1.0.0',
	description='This is a simple module for making requests to OpenAI (ChatGPT) in asynchronous manner using coroutines.',
	long_description=long_description,
	long_description_content_type='text/markdown',
	author='Ioann Volkov',
	author_email='volkov.ioann@gmail.com',
	url='https://github.com/Tsar/async_openai_requests',
)
