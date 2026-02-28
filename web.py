"""
Shared Jinja2Templates instance.

Import from here so both route modules use the same object and template
directory is declared in exactly one place.
"""

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
