# --- File: operators/view_navigator.py ---
import bpy
import math
from mathutils import Euler

class VIEW_OT_set_view_axis(bpy.types.Operator):
    """Sets the 3D view to a specified axis using Blender's internal tools."""
    bl_idname = "view.set_axis"
    bl_label = "Set View Axis"
    bl_options = {'REGISTER', 'UNDO'}

    view_type: bpy.props.StringProperty()

    def execute(self, context):
        # Find a 3D view area and region to run the operator in
        area = next((a for a in context.screen.areas if a.type == 'VIEW_3D'), None)
        if not area:
            self.report({'WARNING'}, "Could not find a 3D Viewport")
            return {'CANCELLED'}

        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        if not region:
            # This can happen if the view is collapsed
            self.report({'WARNING'}, "Could not find a 3D Viewport window region")
            return {'CANCELLED'}

        # Create the explicit override context dictionary
        override = {
            'area': area,
            'region': region,
            'space_data': area.spaces.active,
            'screen': context.screen,
            'window': context.window,
        }

        settings = context.scene.cad_tool_settings
        
        if self.view_type == 'PERSP':
            bpy.ops.view3d.view_perspective(override)
        else:
            # Check the perspective from the correct space_data in the override
            if area.spaces.active.region_3d.view_perspective != 'ORTHO':
                bpy.ops.view3d.view_ortho(override)
            bpy.ops.view3d.view_axis(override, type=self.view_type)

        bpy.ops.view3d.view_all(override, center=False)

        # After changing view, update the pan origin for the new orientation
        settings.pan_x = 0.0
        settings.pan_y = 0.0
        # The context for accessing space_data properties should be the overridden one
        settings.pan_origin = area.spaces.active.region_3d.view_location.copy()

        return {'FINISHED'}

classes = (
    VIEW_OT_set_view_axis,
)
