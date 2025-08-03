#
# Blender Addon: Engineering CAD Tools - Core Sketcher v22
#
# This script creates a foundational CAD environment in Blender.
#
# Version 22 Changes:
# - FIXED: The persistent RuntimeError and ValueError by implementing the
#   standard `with context.temp_override()` method for operator calls.
# - This definitive fix ensures the operator has the full context it needs
#   to run reliably, correctly orienting the grid in all views.
#
bl_info = {
    "name": "Engineering CAD Tools",
    "author": "Your Name",
    "version": (0, 22, 0),
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > CAD Tools",
    "description": "Core sketching and modeling tools for precision design.",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
}

# Import all the modules that contain your classes
from . import properties
from . import utils
from .operators import view_navigator, op_3d, sketch_tools
from .ui import panel

# A list of all modules that have their own register() functions
modules = [
    properties,
    view_navigator,
    op_3d,
    sketch_tools,
    panel,
]

def register():
    for m in modules:
        m.register()

def unregister():
    for m in reversed(modules):
        m.unregister()

if __name__ == "__main__":
    register()