# --- File: ui/panel.py ---
import bpy

# Import all the operator classes that the panel needs to reference.
# The '..' means "go up one directory level" from ui/ to the addon root.
from ..operators.view_navigator import VIEW_OT_set_view_axis
from ..operators.sketch_tools import (
    SKETCH_OT_draw_line,
    # SKETCH_OT_draw_rectangle, SKETCH_OT_draw_circle,
    # SKETCH_OT_draw_polyline, SKETCH_OT_draw_arc, SKETCH_OT_draw_circle_diameter
)
from ..operators.op_3d import (
    MESH_OT_simple_extrude, MESH_OT_inset_faces, MESH_OT_offset_edges, MESH_OT_bevel_edges,
    MESH_OT_create_hole, MESH_OT_create_gear, MESH_OT_inner_radius
)
from ..operators.reference_manager import IMAGE_OT_load_reference, IMAGE_OT_clear_reference
from ..operators.feature_manager import (
    OBJECT_OT_add_feature, OBJECT_OT_remove_feature, OBJECT_OT_move_feature
)

# --- IMPORTANT: Assume SceneCADSettings and other PropertyGroups are defined and registered in properties.py ---
# You MUST ensure these classes (SceneCADSettings, ImageSettings) are defined in your 'properties.py' file
# and that 'properties.py' is correctly registered in your addon's __init__.py.
# This file (ui/panel.py) will now just import and use them.
try:
    from .. import properties as addon_properties
except ImportError:
    print("Warning: Could not import 'properties' module. Ensure SceneCADSettings is defined and registered.")
    # Fallback/dummy classes to prevent immediate errors if properties.py is missing or malformed
    class SceneCADSettings(bpy.types.PropertyGroup):
        use_vertex_snap: bpy.props.BoolProperty(name="Vertex Snap", default=True)
        use_grid_snap: bpy.props.BoolProperty(name="Grid Snap", default=True)
        use_fill: bpy.props.BoolProperty(name="Auto Fill Closed Shapes", default=False)
        expand_feature_tree: bpy.props.BoolProperty(default=True)
        expand_view_navigator: bpy.props.BoolProperty(default=True)
        expand_reference_sketches: bpy.props.BoolProperty(default=True)
        expand_units_and_grid: bpy.props.BoolProperty(default=True)
        expand_2d_sketching: bpy.props.BoolProperty(default=True)
        expand_3d_operations: bpy.props.BoolProperty(default=True)
        show_ref_sketches: bpy.props.BoolProperty(default=True)
        unit_system: bpy.props.EnumProperty(items=[('METRIC', "Metric", "")])
        metric_unit: bpy.props.EnumProperty(items=[('MM', "Millimeters", "")])
        show_grid: bpy.props.BoolProperty(default=True)
        grid_spacing: bpy.props.FloatProperty(default=1.0)
        show_grid_dimensions: bpy.props.BoolProperty(default=True)
        grid_dimension_font_size: bpy.props.IntProperty(default=12)
        grid_dimension_color: bpy.props.FloatVectorProperty(size=4, default=(1.0,1.0,1.0,1.0))
        # Dummy ImageSettings for fallback
        class ImageSettings(bpy.types.PropertyGroup):
            filepath: bpy.props.StringProperty()
            size: bpy.props.FloatProperty(default=1.0)
            opacity: bpy.props.FloatProperty(default=0.5)
            offset_x: bpy.props.FloatProperty(default=0.0)
            offset_y: bpy.props.FloatProperty(default=0.0)
        top_image: bpy.props.PointerProperty(type=ImageSettings)
        front_image: bpy.props.PointerProperty(type=ImageSettings)
        right_image: bpy.props.PointerProperty(type=ImageSettings)
        bottom_image: bpy.props.PointerProperty(type=ImageSettings)
        back_image: bpy.props.PointerProperty(type=ImageSettings)
        left_image: bpy.props.PointerProperty(type=ImageSettings)

    # If addon_properties is not available, we'll use the dummy SceneCADSettings
    addon_properties = type('DummyProperties', (object,), {'SceneCADSettings': SceneCADSettings})()


class OBJECT_UL_feature_tree(bpy.types.UIList):
    """UIList for displaying the feature tree."""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # data is the object, item is the feature
        obj = data
        feature = item

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # Default icon
            op_icon = 'MODIFIER'
            if feature.type == 'EXTRUDE':
                op_icon = 'MOD_SOLIDIFY'
            elif feature.type == 'BEVEL':
                op_icon = 'MOD_BEVEL'

            layout.label(text=feature.name, icon=op_icon)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)


class VIEW3D_PT_cad_tools(bpy.types.Panel):
    bl_label = "CAD Tools"
    bl_idname = "VIEW3D_PT_cad_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'CAD Tools'

    def _draw_ref_image_ui(self, layout, scene_settings, view_name, view_type):
        """Helper function to draw the UI for a single reference image view."""
        # Ensure image_settings is accessible and has a 'filepath' property
        image_settings = getattr(scene_settings, f"{view_name.lower()}_image", None)
        
        box = layout.box()
        row = box.row()
        icon = 'IMAGE_DATA' if (image_settings and image_settings.filepath) else 'NONE'
        row.label(text=view_name, icon=icon)
        
        if image_settings and image_settings.filepath:
            clear_op = row.operator(IMAGE_OT_clear_reference.bl_idname, text="Clear", icon='TRASH')
            clear_op.view_type = view_type
        load_op = row.operator(IMAGE_OT_load_reference.bl_idname, text="Load", icon='FILE_FOLDER')
        load_op.view_type = view_type
        
        if image_settings and image_settings.filepath:
            col = box.column(align=True)
            col.use_property_split = True
            col.prop(image_settings, "size")
            col.prop(image_settings, "opacity")
            col.prop(image_settings, "offset_x")
            col.prop(image_settings, "offset_y")

    def draw(self, context):
        layout = self.layout
        scene_settings = context.scene.scene_cad_settings
        obj = context.object

        # --- Feature Tree Section ---
        if obj:
            # Check if the object has our custom property group
            if hasattr(obj, 'object_cad_settings'):
                obj_settings = obj.object_cad_settings
                ft_box = layout.box()
                row = ft_box.row()
                row.prop(obj_settings, "expand_feature_tree", text="Feature Tree", icon='MODIFIER')
                if obj_settings.expand_feature_tree:
                    ft_box.template_list(
                        "OBJECT_UL_feature_tree", # The name of the UIList class
                        "", # list_id (unused)
                        obj_settings,          # data: the property group containing the collection
                        "feature_tree",        # property_name: the name of the collection property
                        obj_settings,          # active_data: the property group containing the active index
                        "active_feature_index" # active_property_name: the name of the active index property
                    )
                    # Add/Remove/Move Buttons
                    row = ft_box.row(align=True)
                    row.operator(OBJECT_OT_add_feature.bl_idname, text="Add", icon='ADD').feature_type = 'EXTRUDE'
                    row.operator(OBJECT_OT_remove_feature.bl_idname, text="Remove", icon='REMOVE')
                    col = row.column(align=True)
                    move_up_op = col.operator(OBJECT_OT_move_feature.bl_idname, text="", icon='TRIA_UP')
                    move_up_op.direction = 'UP'
                    move_down_op = col.operator(OBJECT_OT_move_feature.bl_idname, text="", icon='TRIA_DOWN')
                    move_down_op.direction = 'DOWN'
        
        # --- View Navigator Section ---
        view_box = layout.box()
        view_box.prop(scene_settings, "expand_view_navigator", text="View Navigator", icon='VIEW3D')
        if scene_settings.expand_view_navigator:
            row = view_box.row(align=True)
            row.operator(VIEW_OT_set_view_axis.bl_idname, text="Top").view_type = 'TOP'
            row.operator(VIEW_OT_set_view_axis.bl_idname, text="Front").view_type = 'FRONT'
            row.operator(VIEW_OT_set_view_axis.bl_idname, text="Right").view_type = 'RIGHT'
            row = view_box.row(align=True)
            row.operator(VIEW_OT_set_view_axis.bl_idname, text="Bottom").view_type = 'BOTTOM'
            row.operator(VIEW_OT_set_view_axis.bl_idname, text="Back").view_type = 'BACK'
            row.operator(VIEW_OT_set_view_axis.bl_idname, text="Left").view_type = 'LEFT'
            row = view_box.row(align=True)
            row.operator(VIEW_OT_set_view_axis.bl_idname, text="Perspective", icon='VIEW_PERSPECTIVE').view_type = 'PERSP'
            col = view_box.column(align=True)
            col.prop(scene_settings, "pan_x", text="L/R")
            col.prop(scene_settings, "pan_y", text="U/D")

        # --- Reference Sketches Section ---
        ref_box = layout.box()
        ref_box.prop(scene_settings, "expand_reference_sketches", text="Reference Sketches", icon='IMAGE_REFERENCE')
        if scene_settings.expand_reference_sketches:
            ref_box.prop(scene_settings, "show_ref_sketches", text="Show/Hide All", toggle=True)
            self._draw_ref_image_ui(ref_box, scene_settings, "Top", "TOP")
            self._draw_ref_image_ui(ref_box, scene_settings, "Front", "FRONT")
            self._draw_ref_image_ui(ref_box, scene_settings, "Right", "RIGHT")
            self._draw_ref_image_ui(ref_box, scene_settings, "Bottom", "BOTTOM")
            self._draw_ref_image_ui(ref_box, scene_settings, "Back", "BACK")
            self._draw_ref_image_ui(ref_box, scene_settings, "Left", "LEFT")

        # --- Units & Grid Section ---
        unit_box = layout.box()
        unit_box.prop(scene_settings, "expand_units_and_grid", text="Units & Grid", icon='GRID')
        if scene_settings.expand_units_and_grid:
            row = unit_box.row(align=True)
            row.prop(scene_settings, "unit_system", expand=True)
            if scene_settings.unit_system == 'METRIC':
                row = unit_box.row(align=True)
                row.prop(scene_settings, "metric_unit", expand=True)
            row = unit_box.row(align=True)
            row.prop(scene_settings, "show_grid", text="Show Grid")
            row.prop(scene_settings, "grid_spacing", text="Spacing")
            unit_box.separator()
            unit_box.prop(scene_settings, "show_grid_dimensions", text="Show Dimensions")
            if scene_settings.show_grid_dimensions:
                col = unit_box.column(align=True)
                col.use_property_split = True
                col.prop(scene_settings, "grid_dimension_font_size", text="Font Size")
                col.prop(scene_settings, "grid_dimension_color", text="Color")

        # --- 2D Sketching Section ---
        sketch_box = layout.box()
        sketch_box.prop(scene_settings, "expand_2d_sketching", text="2D Sketching", icon='GREASEPENCIL')
        if scene_settings.expand_2d_sketching:
            row = sketch_box.row(align=True)
            row.operator(SKETCH_OT_draw_line.bl_idname, text="Line", icon='CURVE_PATH')
            # The following operators are not yet implemented
            # row.operator(SKETCH_OT_draw_rectangle.bl_idname, text="Rectangle", icon='MESH_PLANE')
            # row.operator(SKETCH_OT_draw_circle.bl_idname, text="Circle", icon='MESH_CIRCLE')
            # row = sketch_box.row(align=True)
            # row.operator(SKETCH_OT_draw_polyline.bl_idname, text="Poly-line", icon='MOD_MULTIRES')
            # row.operator(SKETCH_OT_draw_arc.bl_idname, text="Arc", icon='CURVE_NCIRCLE')
            # row.operator(SKETCH_OT_draw_circle_diameter.bl_idname, text="2P Circle", icon='MESH_CIRCLE')
            col = sketch_box.column(align=True)
            col.prop(scene_settings, "use_grid_snap")
            col.prop(scene_settings, "use_vertex_snap")
            # --- New: Auto Fill Closed Shapes option ---
            col.prop(scene_settings, "use_fill")

        # --- 3D Operations Section ---
        op_box = layout.box()
        op_box.prop(scene_settings, "expand_3d_operations", text="3D Operations", icon='MODIFIER')
        if scene_settings.expand_3d_operations:
            op_box.operator(MESH_OT_simple_extrude.bl_idname, text="Extrude", icon='MOD_SOLIDIFY')
            op_box.operator(MESH_OT_inset_faces.bl_idname, text="Inset", icon='FACESEL')
            op_box.operator(MESH_OT_offset_edges.bl_idname, text="Offset", icon='EDGESEL')
            op_box.operator(MESH_OT_bevel_edges.bl_idname, text="Bevel", icon='MOD_BEVEL')
            op_box.separator()
            op_box.operator(MESH_OT_create_hole.bl_idname, text="Hole Tool", icon='MESH_CYLINDER')
            op_box.operator(MESH_OT_inner_radius.bl_idname, text="Inner Radius", icon='MESH_TORUS')
            op_box.operator(MESH_OT_create_gear.bl_idname, text="Spur Gear", icon='MOD_ARRAY')


classes = (
    OBJECT_UL_feature_tree,
    VIEW3D_PT_cad_tools,
)

def register():
    # We assume addon_properties.SceneCADSettings is registered in properties.py
    # and the PointerProperty on bpy.types.Scene is also handled there.
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
