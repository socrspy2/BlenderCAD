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

import bpy

# Import all the modules that contain your classes
from . import properties
from . import utils
from .operators import view_navigator, op_3d, sketch_tools
from .ui import panel

# Combine all classes from all modules (except properties) into a single tuple.
# We will handle properties registration separately due to its special logic.
classes = (
    *view_navigator.classes,
    *op_3d.classes,
    *sketch_tools.classes,
    *panel.classes,
)

def register():
    # Register all the classes from the tuple
    for cls in classes:
        bpy.utils.register_class(cls)

    # Now, handle the registration for the properties module, which includes
    # setting up the PropertyGroup on the scene.
    properties.register()

def unregister():
    # Unregister in the reverse order. Start with the properties.
    properties.unregister()

    # Then unregister all the other classes.
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()