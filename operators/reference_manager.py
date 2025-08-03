# --- File: operators/reference_manager.py ---
import bpy
import math
from bpy_extras.io_utils import ImportHelper

class IMAGE_OT_load_reference(bpy.types.Operator, ImportHelper):
    """Load a reference image for a specific view"""
    bl_idname = "image.load_reference"
    bl_label = "Load Reference Image"
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: bpy.props.StringProperty(default='*.png;*.jpg;*.jpeg;*.bmp;*.tif', options={'HIDDEN'})
    view_type: bpy.props.StringProperty()

    def execute(self, context):
        settings = context.scene.cad_tool_settings
        image_settings_key = f"{self.view_type.lower()}_image"
        image_settings = getattr(settings, image_settings_key)
        empty_name = f"ref_{self.view_type.lower()}"

        if image_settings.empty_ref:
            bpy.data.objects.remove(image_settings.empty_ref, do_unlink=True)

        empty = bpy.data.objects.new(empty_name, None)
        empty.empty_display_type = 'IMAGE'
        context.collection.objects.link(empty)

        try:
            img = bpy.data.images.load(self.filepath)
            empty.data = img
        except Exception as e:
            self.report({'ERROR'}, f"Could not load image: {e}")
            bpy.data.objects.remove(empty, do_unlink=True)
            return {'CANCELLED'}

        if self.view_type == 'FRONT':
            empty.rotation_euler = (math.radians(90), 0, 0)
        elif self.view_type == 'RIGHT':
            empty.rotation_euler = (math.radians(90), 0, math.radians(90))
        elif self.view_type == 'BACK':
            empty.rotation_euler = (math.radians(90), 0, math.radians(180))
        elif self.view_type == 'LEFT':
            empty.rotation_euler = (math.radians(90), 0, math.radians(-90))
        elif self.view_type == 'BOTTOM':
            empty.rotation_euler = (math.radians(180), 0, 0)

        image_settings.filepath = self.filepath
        image_settings.empty_ref = empty

        if empty:
            empty.empty_display_size = image_settings.size
            empty.location.x = image_settings.offset_x
            empty.location.y = image_settings.offset_y
            empty.image_opacity = image_settings.opacity
            empty.hide_viewport = not settings.show_ref_sketches

        return {'FINISHED'}

class IMAGE_OT_clear_reference(bpy.types.Operator):
    """Clears the reference image for a specific view"""
    bl_idname = "image.clear_reference"
    bl_label = "Clear Reference Image"
    bl_options = {'REGISTER', 'UNDO'}

    view_type: bpy.props.StringProperty()

    def execute(self, context):
        settings = context.scene.cad_tool_settings
        image_settings_key = f"{self.view_type.lower()}_image"
        image_settings = getattr(settings, image_settings_key)

        if image_settings.empty_ref:
            img_data = image_settings.empty_ref.data
            bpy.data.objects.remove(image_settings.empty_ref, do_unlink=True)
            if img_data and img_data.users == 0:
                bpy.data.images.remove(img_data)

        image_settings.filepath = ""
        image_settings.empty_ref = None

        return {'FINISHED'}


classes = (
    IMAGE_OT_load_reference,
    IMAGE_OT_clear_reference,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
