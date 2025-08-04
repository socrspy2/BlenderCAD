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
    MESH_OT_create_hole, MESH_OT_create_gear
)
from ..operators.reference_manager import IMAGE_OT_load_reference, IMAGE_OT_clear_reference
from ..operators.feature_manager import (
    OBJECT_OT_add_feature, OBJECT_OT_remove_feature, OBJECT_OT_move_feature
)


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

    def _draw_ref_image_ui(self, layout, settings, view_name, view_type):
        """Helper function to draw the UI for a single reference image view."""
        image_settings = getattr(settings, f"{view_name.lower()}_image")
        box = layout.box()
        row = box.row()
        icon = 'IMAGE_DATA' if image_settings.filepath else 'NONE'
        row.label(text=view_name, icon=icon)
        if image_settings.filepath:
            clear_op = row.operator(IMAGE_OT_clear_reference.bl_idname, text="Clear", icon='TRASH')
            clear_op.view_type = view_type
        load_op = row.operator(IMAGE_OT_load_reference.bl_idname, text="Load", icon='FILE_FOLDER')
        load_op.view_type = view_type
        if image_settings.filepath:
            col = box.column(align=True)
            col.use_property_split = True
            col.prop(image_settings, "size")
            col.prop(image_settings, "opacity")
            col.prop(image_settings, "offset_x")
            col.prop(image_settings, "offset_y")

    def draw(self, context):
        layout = self.layout
        settings = context.scene.cad_tool_settings
        obj = context.object

        # --- Feature Tree Section ---
        if obj:
            # Check if the object has our custom property group
            if hasattr(obj, 'cad_tool_settings'):
                obj_settings = obj.cad_tool_settings
                ft_box = layout.box()
                row = ft_box.row()
                row.prop(obj_settings, "expand_feature_tree", text="Feature Tree", icon='OUTLINER_DATA_MODIFIER')
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
        view_box.prop(settings, "expand_view_navigator", text="View Navigator", icon='VIEW3D')
        if settings.expand_view_navigator:
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
            col.prop(settings, "pan_x", text="L/R")
            col.prop(settings, "pan_y", text="U/D")

        # --- Reference Sketches Section ---
        ref_box = layout.box()
        ref_box.prop(settings, "expand_reference_sketches", text="Reference Sketches", icon='IMAGE')
        if settings.expand_reference_sketches:
            ref_box.prop(settings, "show_ref_sketches", text="Show/Hide All", toggle=True)
            self._draw_ref_image_ui(ref_box, settings, "Top", "TOP")
            self._draw_ref_image_ui(ref_box, settings, "Front", "FRONT")
            self._draw_ref_image_ui(ref_box, settings, "Right", "RIGHT")
            self._draw_ref_image_ui(ref_box, settings, "Bottom", "BOTTOM")
            self._draw_ref_image_ui(ref_box, settings, "Back", "BACK")
            self._draw_ref_image_ui(ref_box, settings, "Left", "LEFT")

        # --- Units & Grid Section ---
        unit_box = layout.box()
        unit_box.prop(settings, "expand_units_and_grid", text="Units & Grid", icon='GRID')
        if settings.expand_units_and_grid:
            row = unit_box.row(align=True)
            row.prop(settings, "unit_system", expand=True)
            if settings.unit_system == 'METRIC':
                row = unit_box.row(align=True)
                row.prop(settings, "metric_unit", expand=True)
            row = unit_box.row(align=True)
            row.prop(settings, "show_grid", text="Show Grid")
            row.prop(settings, "grid_spacing", text="Spacing")
            unit_box.separator()
            unit_box.prop(settings, "show_grid_dimensions", text="Show Dimensions")
            if settings.show_grid_dimensions:
                col = unit_box.column(align=True)
                col.use_property_split = True
                col.prop(settings, "grid_dimension_font_size", text="Font Size")
                col.prop(settings, "grid_dimension_color", text="Color")

        # --- 2D Sketching Section ---
        sketch_box = layout.box()
        sketch_box.prop(settings, "expand_2d_sketching", text="2D Sketching", icon='GREASEPENCIL')
        if settings.expand_2d_sketching:
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
            col.prop(settings, "use_grid_snap")
            col.prop(settings, "use_vertex_snap")

        # --- 3D Operations Section ---
        op_box = layout.box()
        op_box.prop(settings, "expand_3d_operations", text="3D Operations", icon='MODIFIER')
        if settings.expand_3d_operations:
            op_box.operator(MESH_OT_simple_extrude.bl_idname, text="Extrude", icon='MOD_SOLIDIFY')
            op_box.operator(MESH_OT_inset_faces.bl_idname, text="Inset", icon='FACESEL')
            op_box.operator(MESH_OT_offset_edges.bl_idname, text="Offset", icon='EDGESEL')
            op_box.operator(MESH_OT_bevel_edges.bl_idname, text="Bevel", icon='MOD_BEVEL')
            op_box.separator()
            op_box.operator(MESH_OT_create_hole.bl_idname, text="Hole Tool", icon='MESH_CYLINDER')
            op_box.operator(MESH_OT_create_gear.bl_idname, text="Spur Gear", icon='MOD_ARRAY')


classes = (
    OBJECT_UL_feature_tree,
    VIEW3D_PT_cad_tools,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
