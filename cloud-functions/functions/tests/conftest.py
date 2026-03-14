import os
import sys

# Ensure `import main` works when running pytest from the repository root.
FUNCTIONS_DIR = os.path.dirname(os.path.dirname(__file__))
if FUNCTIONS_DIR not in sys.path:
    sys.path.insert(0, FUNCTIONS_DIR)
