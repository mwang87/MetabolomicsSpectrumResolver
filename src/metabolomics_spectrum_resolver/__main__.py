# -*- coding: utf-8 -*-

"""Entrypoint module, in case you use ``python -m metabolomics_spectrum_resolver``.

Why does this file exist, and why ``__main__``? For more info, read:
 - https://www.python.org/dev/peps/pep-0338/
 - https://docs.python.org/3/using/cmdline.html#cmdoption-m
"""

from metabolomics_spectrum_resolver.cli import main

if __name__ == '__main__':
    main()
