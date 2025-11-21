"""
Setup script for abtest-culprits package.
"""

from setuptools import setup, find_packages
import os


def read_requirements():
    """Read requirements from requirements.txt."""
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    with open(requirements_path) as f:
        requirements = []
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                requirements.append(line)
        return requirements


def read_long_description():
    """Read long description from README.md."""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


setup(
    name='abtest-culprits',
    version='0.1.0',
    description='Automated diagnostic framework for cross-platform A/B test analysis',
    long_description=read_long_description(),
    long_description_content_type='text/markdown',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/ABTest-Culprits',
    packages=find_packages(exclude=['tests', 'examples', 'docs']),
    install_requires=read_requirements(),
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    keywords='ab-testing experimentation statistics data-analysis cross-platform',
    project_urls={
        'Bug Reports': 'https://github.com/yourusername/ABTest-Culprits/issues',
        'Source': 'https://github.com/yourusername/ABTest-Culprits',
        'Documentation': 'https://github.com/yourusername/ABTest-Culprits/tree/main/docs',
    },
)
