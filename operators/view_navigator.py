# --- File: operators/view_navigator.py ---
import bpy

class VIEW_OT_set_view_axis(bpy.types.Operator):
    """Sets the 3D view to a specified axis using Blender's internal tools."""
    bl_idname = "view.set_axis"
    bl_label = "Set View Axis"
    bl_options = {'REGISTER', 'UNDO'}

    view_type: bpy.props.StringProperty()

    def execute(self, context):
        # Find the first available 3D Viewport area to run the operator in.
        area = next((a for a in context.screen.areas if a.type == 'VIEW_3D'), None)
        if not area:
            self.report({'WARNING'}, "Could not find a 3D Viewport")
            return {'CANCELLED'}

        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        if not region:
            self.report({'WARNING'}, "Could not find a 3D Viewport window region")
            return {'CANCELLED'}

        settings = context.scene.cad_tool_settings
        
        # Use the standard and most robust method for context override.
        with context.temp_override(area=area, region=region):
            if self.view_type == 'PERSP':
                bpy.ops.view3d.view_perspective()
            else:
                if area.spaces.active.region_3d.view_perspective != 'ORTHO':
                    bpy.ops.view3d.view_ortho()
                bpy.ops.view3d.view_axis(type=self.view_type)

            bpy.ops.view3d.view_all(center=False)

            settings.pan_x = 0.0
            settings.pan_y = 0.0
            settings.pan_origin = area.spaces.active.region_3d.view_location.copy()

        return {'FINISHED'}

classes = (
    VIEW_OT_set_view_axis,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
