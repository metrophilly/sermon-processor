import os

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEMPLATE_DIR = os.path.join(SCRIPT_DIR, "templates")

OUTPUT_BASE_DIR = os.path.join(SCRIPT_DIR, "data")
