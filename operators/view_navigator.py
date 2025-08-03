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
        area_3d = next((a for a in context.screen.areas if a.type == 'VIEW_3D'), None)
        if area_3d is None:
            self.report({'WARNING'}, "Could not find a 3D Viewport")
            return {'CANCELLED'}

        settings = context.scene.cad_tool_settings
        
        with context.temp_override(area=area_3d, region=next(r for r in area_3d.regions if r.type == 'WINDOW')):
            if self.view_type == 'PERSP':
                bpy.ops.view3d.view_perspective()
            else:
                if context.space_data.region_3d.view_perspective != 'ORTHO':
                    bpy.ops.view3d.view_ortho()
                bpy.ops.view3d.view_axis(type=self.view_type)

            bpy.ops.view3d.view_all(center=False)
            settings.pan_x = 0.0
            settings.pan_y = 0.0
            settings.pan_origin = context.space_data.region_3d.view_location.copy()

        return {'FINISHED'}

classes = (
    VIEW_OT_set_view_axis,
)
