# -*- coding: utf-8 -*-
"""
Installs:
    - cor-asv-fst-train
"""
import codecs

from setuptools import Extension, setup, find_packages

# FIXME restore this!
# cfg_vars = get_config_vars()
# for key, value in cfg_vars.items():
#     if type(value) == str:
#         cfg_vars[key] = value.replace("-Wstrict-prototypes", "")


with codecs.open('README.md', encoding='utf-8') as f:
    README = f.read()

setup(
    name='cor_asv_fst',
    version='0.1.0',
    description='OCR post-correction with error/lexicon Finite State '
                'Transducers and character-level LSTMs',
    long_description=README,
    author='Maciej Sumalvico, Robert Sachunsky',
    author_email='sumalvico@informatik.uni-leipzig.de, '
                 'sachunsky@informatik.uni-leipzig.de',
    url='https://github.com/ASVLeipzig/cor-asv-fst',
    license='Apache License 2.0',
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=[
        'ocrd >= 0.15.2',
        'ocrd_keraslm >= 0.3.1',
        'click',
        'cython',
        'numpy',
        'hfst',
        'networkx',
        'nltk',
        'spacy',
        'editdistance',
    ],
    package_data={
        '': ['*.json', '*.yml', '*.yaml'],
    },
    entry_points={
        'console_scripts': [
            'cor-asv-fst-train=scripts.run:cli',
            'ocrd-cor-asv-fst-process=cor_asv_fst.wrapper.cli:cor_asv_fst',
        ]
    },
    ext_modules=[
        Extension(
            "cor_asv_fst.lib.extensions.composition",
            sources=[
                "cor_asv_fst/lib/extensions/composition.pyx",
                "cor_asv_fst/lib/extensions/composition_cpp.cpp"],
            libraries=["fst", "dl"],
            language="c++")
        ],
)