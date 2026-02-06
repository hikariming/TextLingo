#!/usr/bin/env python3
"""
PyInstaller entry point wrapper.
Uses absolute imports to avoid 'relative import with no known parent package' error.
"""
import sys
from openkoto_pdf_translator.pdf2zh import main

sys.exit(main())
