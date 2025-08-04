# --- File: operators/feature_manager.py ---
import bpy

class OBJECT_OT_add_feature(bpy.types.Operator):
    """Add a new feature to the active object's feature tree."""
    bl_idname = "object.add_feature"
    bl_label = "Add Feature"
    bl_options = {'REGISTER', 'UNDO'}

    feature_type: bpy.props.EnumProperty(
        items=[
            ('EXTRUDE', "Extrude", "Add an extrude feature"),
            ('BEVEL', "Bevel", "Add a bevel feature"),
        ],
        name="Feature Type"
    )

    def execute(self, context):
        obj = context.object
        if not obj:
            self.report({'WARNING'}, "No active object selected.")
            return {'CANCELLED'}

        # In a real implementation, we would add a feature of the specified type.
        # For now, just a placeholder.
        self.report({'INFO'}, f"Placeholder: Add {self.feature_type} feature.")
        # Example of how it would work:
        # new_feature = obj.object_cad_settings.feature_tree.add()
        # new_feature.name = self.feature_type.capitalize()
        # new_feature.type = self.feature_type
        return {'FINISHED'}


class OBJECT_OT_remove_feature(bpy.types.Operator):
    """Remove the selected feature from the tree."""
    bl_idname = "object.remove_feature"
    bl_label = "Remove Feature"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.object_cad_settings and len(obj.object_cad_settings.feature_tree) > 0

    def execute(self, context):
        obj = context.object
        settings = obj.object_cad_settings
        index = settings.active_feature_index

        # In a real implementation, we would remove the feature.
        # For now, just a placeholder.
        self.report({'INFO'}, f"Placeholder: Remove feature at index {index}.")
        # Example of how it would work:
        # settings.feature_tree.remove(index)
        # settings.active_feature_index = min(max(0, index - 1), len(settings.feature_tree) - 1)
        return {'FINISHED'}


class OBJECT_OT_move_feature(bpy.types.Operator):
    """Move the selected feature up or down in the tree."""
    bl_idname = "object.move_feature"
    bl_label = "Move Feature"
    bl_options = {'REGISTER', 'UNDO'}

    direction: bpy.props.EnumProperty(
        items=[
            ('UP', "Up", "Move feature up"),
            ('DOWN', "Down", "Move feature down"),
        ],
        name="Direction"
    )

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.object_cad_settings and len(obj.object_cad_settings.feature_tree) > 1

    def execute(self, context):
        obj = context.object
        settings = obj.object_cad_settings
        index = settings.active_feature_index

        # In a real implementation, we would move the feature.
        # For now, just a placeholder.
        self.report({'INFO'}, f"Placeholder: Move feature {self.direction}.")
        # Example of how it would work:
        # if self.direction == 'UP':
        #     if index > 0:
        #         settings.feature_tree.move(index, index - 1)
        #         settings.active_feature_index -= 1
        # elif self.direction == 'DOWN':
        #     if index < len(settings.feature_tree) - 1:
        #         settings.feature_tree.move(index, index + 1)
        #         settings.active_feature_index += 1
        return {'FINISHED'}


classes = (
    OBJECT_OT_add_feature,
    OBJECT_OT_remove_feature,
    OBJECT_OT_move_feature,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
