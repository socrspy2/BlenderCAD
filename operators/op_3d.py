# --- File: operators/3d_operations.py ---
import bpy

class MESH_OT_simple_extrude(bpy.types.Operator):
    """Extrudes the selected faces of the active object."""
    bl_idname = "mesh.simple_extrude"
    bl_label = "Extrude"
    bl_options = {'REGISTER', 'UNDO'}

    extrude_depth: bpy.props.FloatProperty(name="Depth", default=1.0, subtype='DISTANCE')

    def execute(self, context):
        if context.active_object and context.active_object.type == 'MESH':
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.extrude_region_move(
                TRANSFORM_OT_translate={"value": (0, 0, self.extrude_depth)}
            )
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            self.report({'WARNING'}, "No active mesh object selected.")
            return {'CANCELLED'}
        return {'FINISHED'}

class MESH_OT_offset_edges(bpy.types.Operator):
    """Offsets the selected edges of the active object."""
    bl_idname = "mesh.offset_edges"
    bl_label = "Offset Edges"
    bl_options = {'REGISTER', 'UNDO'}

    offset_distance: bpy.props.FloatProperty(name="Distance", default=0.2, subtype='DISTANCE')

    def execute(self, context):
        if context.active_object and context.active_object.type == 'MESH':
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.offset_edges(geometry_mode='extrude', use_even=True, amount=self.offset_distance)
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            self.report({'WARNING'}, "No active mesh object selected.")
            return {'CANCELLED'}
        return {'FINISHED'}

class MESH_OT_inset_faces(bpy.types.Operator):
    """Insets the selected faces of the active object."""
    bl_idname = "mesh.inset_faces"
    bl_label = "Inset Faces"
    bl_options = {'REGISTER', 'UNDO'}

    inset_thickness: bpy.props.FloatProperty(name="Thickness", default=0.2, subtype='DISTANCE')
    inset_depth: bpy.props.FloatProperty(name="Depth", default=0.0, subtype='DISTANCE')

    def execute(self, context):
        if context.active_object and context.active_object.type == 'MESH':
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.inset(thickness=self.inset_thickness, depth=self.inset_depth)
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            self.report({'WARNING'}, "No active mesh object selected.")
            return {'CANCELLED'}
        return {'FINISHED'}

class MESH_OT_bevel_edges(bpy.types.Operator):
    """Bevels the selected edges of the active object."""
    bl_idname = "mesh.bevel_edges"
    bl_label = "Bevel Edges"
    bl_options = {'REGISTER', 'UNDO'}

    bevel_amount: bpy.props.FloatProperty(name="Amount", default=0.2, subtype='DISTANCE')
    bevel_segments: bpy.props.IntProperty(name="Segments", default=4, min=1)

    def execute(self, context):
        if context.active_object and context.active_object.type == 'MESH':
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.bevel(offset=self.bevel_amount, segments=self.bevel_segments)
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            self.report({'WARNING'}, "No active mesh object selected.")
            return {'CANCELLED'}
        return {'FINISHED'}

classes = (
    MESH_OT_simple_extrude,
    MESH_OT_offset_edges,
    MESH_OT_inset_faces,
    MESH_OT_bevel_edges,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)