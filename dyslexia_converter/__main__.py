"""``python -m dyslexia_converter``: the command line (see cli.py); the app itself starts with main.py."""
from .cli import main
import sys

sys.exit(main())
