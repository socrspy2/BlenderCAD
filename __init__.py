# This is the main __init__.py file for your addon.
# It should be located at: /BlenderCAD-main/__init__.py

bl_info = {
    "name": "Engineering CAD Tools",
    "author": "Your Name",
    "version": (1, 0, 0), # Updated to 1.0.0 as this is a major refactor
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > CAD Tools",
    "description": "A non-destructive, parametric CAD environment for Blender.",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
}

import bpy

# Import all the modules that contain your classes
from . import properties
from .operators import view_navigator, op_3d, sketch_tools, reference_manager, feature_manager
from .ui import panel, draw_handlers

# A list of all modules that have their own register() functions
modules = [
    properties,
    view_navigator,
    op_3d,
    sketch_tools,
    reference_manager,
    feature_manager,
    panel,
    draw_handlers,
]

def register():
    """This function is called when the addon is enabled."""
    # Loop through all our modules and call their individual register() functions.
    for m in modules:
        m.register()

def unregister():
    """This function is called when the addon is disabled."""
    # It's important to unregister in the reverse order to avoid issues.
    for m in reversed(modules):
        m.unregister()

if __name__ == "__main__":
    register()
