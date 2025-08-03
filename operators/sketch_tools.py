# --- File: operators/sketch_tools.py ---
import bpy
import bmesh
import gpu
import blf
import math
from mathutils import Vector
from bpy_extras.view3d_utils import location_3d_to_region_2d
from ..utils import mouse_to_plane_coord, draw_circle_3d, draw_text_2d

class SketcherModalBase(bpy.types.Operator):
    """Base class for modal sketching operators."""
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        self.active = True
        self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, (context,), 'WINDOW', 'POST_VIEW')
        context.window_manager.modal_handler_add(self)
        self.original_cursor = context.window.cursor
        context.window.cursor_set('CROSSHAIR')
        return {'RUNNING_MODAL'}

    def cleanup(self, context):
        context.window.cursor_set(self.original_cursor)
        context.area.header_text_set(None)
        if self.draw_handle:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, 'WINDOW')
        self.active = False

    def get_snapped_point(self, context, event):
        """Calculates the 3D mouse position with snapping."""
        settings = context.scene.cad_tool_settings
        snapped_vertex_pos = None

        temp_mouse_pos = mouse_to_plane_coord(context, event)
        if temp_mouse_pos is None: return None, None

        if settings.use_vertex_snap:
            snap_threshold_px = 10
            best_dist_sq = snap_threshold_px**2
            depsgraph = context.evaluated_depsgraph_get()
            for obj in context.visible_objects:
                if obj.type == 'MESH':
                    world_matrix = obj.matrix_world
                    mesh = obj.evaluated_get(depsgraph).to_mesh()
                    for v in mesh.vertices:
                        v_world = world_matrix @ v.co
                        v_2d = location_3d_to_region_2d(context.region, context.region_data, v_world)
                        if v_2d:
                            dist_sq = (v_2d.x - event.mouse_region_x)**2 + (v_2d.y - event.mouse_region_y)**2
                            if dist_sq < best_dist_sq:
                                best_dist_sq = dist_sq
                                snapped_vertex_pos = v_world
            if snapped_vertex_pos:
                return snapped_vertex_pos, snapped_vertex_pos

        if settings.use_grid_snap:
            scale = context.space_data.overlay.grid_scale
            temp_mouse_pos.x = round(temp_mouse_pos.x / scale) * scale
            temp_mouse_pos.y = round(temp_mouse_pos.y / scale) * scale
            temp_mouse_pos.z = round(temp_mouse_pos.z / scale) * scale

        return temp_mouse_pos, snapped_vertex_pos

class SKETCH_OT_draw_line(SketcherModalBase):
    bl_idname = "sketch.draw_line"
    bl_label = "Draw Line"

    def invoke(self, context, event):
        self.points = []
        self.snapped_vertex_pos = None
        context.area.header_text_set("Line: Click for start point. ESC to cancel.")
        return super().invoke(context, event)

    def modal(self, context, event):
        if not self.active: return {'FINISHED'}
        
        self.mouse_pos_3d, self.snapped_vertex_pos = self.get_snapped_point(context, event)
        if self.mouse_pos_3d is None: return {'PASS_THROUGH'}
        
        context.area.tag_redraw()

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.points.append(self.mouse_pos_3d)
            if len(self.points) == 2:
                self.finish_drawing(context)
                return {'FINISHED'}
            context.area.header_text_set("Line: Click for end point.")
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cleanup(context)
            return {'CANCELLED'}
        return {'PASS_THROUGH'}

    def draw_callback_px(self, context):
        # Draw snapping indicators first
        if self.snapped_vertex_pos:
            p_2d = location_3d_to_region_2d(context.region, context.region_data, self.snapped_vertex_pos)
            if p_2d:
                shader_2d = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
                circle = draw_circle_3d(p_2d, 8, Vector((0,0,1)), segments=12)
                batch = batch_for_shader(shader_2d, 'LINE_STRIP', {"pos": circle})
                shader_2d.bind()
                shader_2d.uniform_float("color", (0.1, 0.8, 0.1, 1.0))
                batch.draw(shader_2d)

        # Draw the line preview
        if self.points and self.mouse_pos_3d:
            shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
            line_verts = [self.points[0], self.mouse_pos_3d]
            batch = batch_for_shader(shader, 'LINES', {"pos": line_verts})
            shader.bind()
            shader.uniform_float("color", (0.1, 0.1, 0.8, 1.0))
            batch.draw(shader)

    def finish_drawing(self, context):
        if len(self.points) < 2:
            self.cleanup(context)
            return

        obj = context.active_object
        if not obj or obj.type != 'MESH':
            bm = bmesh.new()
            v1 = bm.verts.new(self.points[0])
            v2 = bm.verts.new(self.points[1])
            bm.edges.new((v1, v2))
            mesh_data = bpy.data.meshes.new("CAD_Sketch_Mesh")
            bm.to_mesh(mesh_data)
            bm.free()
            obj = bpy.data.objects.new("CAD_Sketch", mesh_data)
            context.collection.objects.link(obj)
        else:
            bpy.ops.object.mode_set(mode='OBJECT')
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            verts = []
            for p in self.points:
                found_vert = next((v for v in bm.verts if (v.co - p).length < 0.0001), None)
                verts.append(found_vert if found_vert else bm.verts.new(p))
            v1, v2 = verts
            if not any(e for e in bm.edges if (e.verts[0] == v1 and e.verts[1] == v2) or (e.verts[0] == v2 and e.verts[1] == v1)):
                 bm.edges.new((v1, v2))
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
            bmesh.ops.contextual_create(bm, geom=bm.edges)
            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        self.cleanup(context)

# ... (Other sketch operators would also inherit from SketcherModalBase)

classes = (
    SKETCH_OT_draw_line,
    # SKETCH_OT_draw_rectangle, # To be updated
    # SKETCH_OT_draw_circle, # To be updated
    # SKETCH_OT_draw_polyline, # To be implemented
    # SKETCH_OT_draw_circle_diameter, # To be implemented
    # SKETCH_OT_draw_arc, # To be implemented
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
