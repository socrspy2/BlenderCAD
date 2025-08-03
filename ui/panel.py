# #############################################################################
# --- UI (would be in 'ui/panel.py') ---
# #############################################################################
import bpy

# --- ADDED: Import the operator classes so the panel can use their bl_idname ---
from ..operators.view_navigator import VIEW_OT_set_view_axis
from ..operators.sketch_tools import SKETCH_OT_draw_line, SKETCH_OT_draw_rectangle, SKETCH_OT_draw_circle
from ..operators.op_3d import MESH_OT_simple_extrude, MESH_OT_inset_faces, MESH_OT_offset_edges, MESH_OT_bevel_edges


class VIEW3D_PT_cad_tools(bpy.types.Panel):
    bl_label = "CAD Tools"
    bl_idname = "VIEW3D_PT_cad_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'CAD Tools'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.cad_tool_settings
        
        # --- View Navigator Section ---
        view_box = layout.box()
        view_box.label(text="View Navigator", icon='VIEW3D')
        
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

        # --- Units & Grid Section ---
        unit_box = layout.box()
        unit_box.label(text="Units & Grid", icon='GRID')
        
        row = unit_box.row(align=True)
        row.prop(settings, "unit_system", expand=True)
        
        if settings.unit_system == 'METRIC':
            row = unit_box.row(align=True)
            row.prop(settings, "metric_unit", expand=True)
        
        row = unit_box.row(align=True)
        row.prop(settings, "show_grid", text="Show Grid")
        row.prop(settings, "grid_spacing", text="Spacing")


        # --- 2D Sketching Section ---
        sketch_box = layout.box()
        sketch_box.label(text="2D Sketching", icon='GREASEPENCIL')
        
        row = sketch_box.row(align=True)
        row.operator(SKETCH_OT_draw_line.bl_idname, text="Line", icon='CURVE_PATH')
        row.operator(SKETCH_OT_draw_rectangle.bl_idname, text="Rectangle", icon='MESH_PLANE')
        row.operator(SKETCH_OT_draw_circle.bl_idname, text="Circle", icon='MESH_CIRCLE')
        
        col = sketch_box.column(align=True)
        col.prop(settings, "use_grid_snap")
        col.prop(settings, "use_vertex_snap")

        # --- 3D Operations Section ---
        op_box = layout.box()
        op_box.label(text="3D Operations", icon='MODIFIER')
        op_box.operator(MESH_OT_simple_extrude.bl_idname, text="Extrude", icon='MOD_SOLIDIFY')
        op_box.operator(MESH_OT_inset_faces.bl_idname, text="Inset", icon='FACESEL')
        op_box.operator(MESH_OT_offset_edges.bl_idname, text="Offset", icon='EDGESEL')
        op_box.operator(MESH_OT_bevel_edges.bl_idname, text="Bevel", icon='MOD_BEVEL')

classes = (
    VIEW3D_PT_cad_tools,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
