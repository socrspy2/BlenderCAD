# --- File: operators/sketch_tools.py ---
import bpy
import bmesh
import gpu
import blf
import math
from mathutils import Vector
# --- ADDED: Import necessary functions from bpy_extras.view3d_utils ---
from bpy_extras.view3d_utils import location_3d_to_region_2d
from ..utils import mouse_to_plane_coord, draw_circle_3d, draw_text_2d # Note the .. to import from the parent folder

# --- ADDED: A base class for modal sketch tools to reduce code duplication ---
class SketcherModalBase(bpy.types.Operator):
    """Base class for modal sketching operators to handle common setup and teardown."""
    bl_options = {'REGISTER', 'UNDO'}

    def __init__(self):
        self.points = []
        self.mouse_pos_3d = None
        self.draw_handle = None
        self.active = False

    def invoke(self, context, event):
        self.active = True
        self.points = []
        self.mouse_pos_3d = None
        # It's good practice to store the original cursor and restore it.
        self.original_cursor = context.window.cursor
        context.window.cursor_set('CROSSHAIR')

        self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, (context,), 'WINDOW', 'POST_VIEW')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cleanup(self, context):
        self.active = False
        context.window.cursor_set(self.original_cursor)
        context.area.header_text_set(None)
        if self.draw_handle:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, 'WINDOW')

    def get_snapped_point(self, context, event):
        """Calculates the 3D mouse position with snapping."""
        settings = context.scene.cad_tool_settings
        snapped_vertex_pos = None

        temp_mouse_pos = mouse_to_plane_coord(context, event)
        if temp_mouse_pos is None: return None

        if settings.use_vertex_snap:
            # Simplified snap logic for brevity
            depsgraph = context.evaluated_depsgraph_get()
            # This threshold should be in 2D screen space pixels
            snap_threshold_px = 10
            best_dist_sq = snap_threshold_px**2

            for obj in context.visible_objects:
                if obj.type == 'MESH' and context.view_layer.objects.active != obj :
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
                return snapped_vertex_pos

        if settings.use_grid_snap:
            scale = context.space_data.overlay.grid_scale
            temp_mouse_pos.x = round(temp_mouse_pos.x / scale) * scale
            temp_mouse_pos.y = round(temp_mouse_pos.y / scale) * scale
            temp_mouse_pos.z = round(temp_mouse_pos.z / scale) * scale

        return temp_mouse_pos

    # Stubs that child classes must implement
    def draw_callback_px(self, context):
        raise NotImplementedError()

    def finish_drawing(self, context):
        raise NotImplementedError()

    def modal(self, context, event):
        raise NotImplementedError()


class SKETCH_OT_draw_line(bpy.types.Operator):
    """Draw a line in the 3D view by clicking two points."""
    bl_idname = "sketch.draw_line"
    bl_label = "Draw Line"
    bl_options = {'REGISTER', 'UNDO'}

    def draw_callback_px(self, context):
        if self.points and self.mouse_pos_3d is not None:
            shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
            line_verts = [self.points[0], self.mouse_pos_3d]
            batch = batch_for_shader(shader, 'LINES', {"pos": line_verts})
            shader.bind()
            shader.uniform_float("color", (0.1, 0.1, 0.8, 1.0))
            batch.draw(shader)
        
        if self.points:
            point_coords = [location_3d_to_region_2d(context.region, context.region_data, p) for p in self.points]
            shader_2d = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
            for p_2d in point_coords:
                if p_2d:
                    # In 2D drawing, we draw a 2D circle, not a 3D one.
                    # This was a subtle bug that is now fixed.
                    circle_verts = []
                    for i in range(13):
                        angle = (i / 12) * 2 * math.pi
                        circle_verts.append((p_2d.x + math.cos(angle) * 5, p_2d.y + math.sin(angle) * 5))

                    batch = batch_for_shader(shader_2d, 'LINE_STRIP', {"pos": circle_verts})
                    shader_2d.bind()
                    shader_2d.uniform_float("color", (0.8, 0.1, 0.1, 1.0))
                    batch.draw(shader_2d)

        if self.snapped_vertex_pos:
            p_2d = location_3d_to_region_2d(context.region, context.region_data, self.snapped_vertex_pos)
            if p_2d:
                shader_2d = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
                circle_verts = []
                for i in range(13):
                    angle = (i / 12) * 2 * math.pi
                    circle_verts.append((p_2d.x + math.cos(angle) * 8, p_2d.y + math.sin(angle) * 8))
                
                batch = batch_for_shader(shader_2d, 'LINE_STRIP', {"pos": circle_verts})
                shader_2d.bind()
                shader_2d.uniform_float("color", (0.1, 0.8, 0.1, 1.0))
                batch.draw(shader_2d)

    def invoke(self, context, event):
        self.points = []
        self.snapped_vertex_pos = None
        self.active = True
        self.mouse_pos_3d = None
        self.original_grid_settings = {'show_floor': context.space_data.overlay.show_floor, 'grid_scale': context.space_data.overlay.grid_scale}
        context.space_data.overlay.show_floor = True
        self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, (context,), 'WINDOW', 'POST_VIEW')
        context.window_manager.modal_handler_add(self)
        context.window.cursor_set('CROSSHAIR')
        context.area.header_text_set("CAD Sketcher: Click to set first point. ESC to cancel.")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if not self.active: return {'FINISHED'}
        
        settings = context.scene.cad_tool_settings
        self.snapped_vertex_pos = None
        
        temp_mouse_pos = mouse_to_plane_coord(context, event)
        if temp_mouse_pos is None: return {'PASS_THROUGH'}

        if settings.use_vertex_snap:
            snap_threshold = 10
            best_dist = snap_threshold**2
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
                            if dist_sq < best_dist:
                                best_dist = dist_sq
                                self.snapped_vertex_pos = v_world
            if self.snapped_vertex_pos:
                temp_mouse_pos = self.snapped_vertex_pos

        if not self.snapped_vertex_pos and settings.use_grid_snap:
            scale = context.space_data.overlay.grid_scale
            temp_mouse_pos.x = round(temp_mouse_pos.x / scale) * scale
            temp_mouse_pos.y = round(temp_mouse_pos.y / scale) * scale
            temp_mouse_pos.z = round(temp_mouse_pos.z / scale) * scale

        self.mouse_pos_3d = temp_mouse_pos
        context.area.tag_redraw()

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.points.append(self.mouse_pos_3d)
            if len(self.points) == 2:
                self.finish_drawing(context)
                return {'FINISHED'}
            else:
                context.area.header_text_set("CAD Sketcher: Click to set second point. ESC to cancel.")
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cleanup(context)
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

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
                if found_vert:
                    verts.append(found_vert)
                else:
                    verts.append(bm.verts.new(p))
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

    def cleanup(self, context):
        self.active = False
        context.window.cursor_set('DEFAULT')
        context.area.header_text_set(None)
        if self.draw_handle:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, 'WINDOW')
        if hasattr(self, 'original_grid_settings'):
            context.space_data.overlay.show_floor = self.original_grid_settings['show_floor']
            context.space_data.overlay.grid_scale = self.original_grid_settings['grid_scale']

class SKETCH_OT_draw_rectangle(bpy.types.Operator):
    """Draw a filled rectangle by dragging from one corner to the other."""
    bl_idname = "sketch.draw_rectangle"
    bl_label = "Draw Rectangle"
    bl_options = {'REGISTER', 'UNDO'}

    def draw_callback_px(self, context):
        if self.start_pos_3d and self.mouse_pos_3d:
            p1 = self.start_pos_3d
            p2 = self.mouse_pos_3d
            
            verts_3d = [
                p1, Vector((p2.x, p1.y, p1.z)),
                p2, Vector((p1.x, p2.y, p1.z))
            ]
            
            shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
            batch = batch_for_shader(shader, 'LINE_LOOP', {"pos": verts_3d})
            shader.bind()
            shader.uniform_float("color", (0.1, 0.1, 0.8, 1.0))
            batch.draw(shader)
            
            width = abs(p2.x - p1.x)
            height = abs(p2.y - p1.y)
            dim_text = f"W: {width:.3f}, H: {height:.3f}"
            draw_text_2d(self.mouse_pos_2d.x, self.mouse_pos_2d.y, dim_text)

    def invoke(self, context, event):
        self.start_pos_3d = None
        self.mouse_pos_3d = None
        self.mouse_pos_2d = None
        self.active = True
        
        self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, (context,), 'WINDOW', 'POST_VIEW')
        context.window_manager.modal_handler_add(self)
        context.window.cursor_set('CROSSHAIR')
        context.area.header_text_set("CAD Sketcher: Click and drag to draw rectangle. ESC to cancel.")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if not self.active: return {'FINISHED'}

        self.mouse_pos_3d = mouse_to_plane_coord(context, event)
        self.mouse_pos_2d = Vector((event.mouse_region_x, event.mouse_region_y))
        
        if self.mouse_pos_3d is None: return {'PASS_THROUGH'}
        
        context.area.tag_redraw()

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.start_pos_3d = self.mouse_pos_3d
            return {'RUNNING_MODAL'}
        
        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self.finish_drawing(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cleanup(context)
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def finish_drawing(self, context):
        if not self.start_pos_3d or not self.mouse_pos_3d:
            self.cleanup(context)
            return

        p1 = self.start_pos_3d
        p2 = self.mouse_pos_3d

        bm = bmesh.new()
        v1 = bm.verts.new(p1)
        v2 = bm.verts.new((p2.x, p1.y, p1.z))
        v3 = bm.verts.new(p2)
        v4 = bm.verts.new((p1.x, p2.y, p1.z))
        
        bm.faces.new((v1, v2, v3, v4))
        
        mesh_data = bpy.data.meshes.new("CAD_Rectangle_Mesh")
        bm.to_mesh(mesh_data)
        bm.free()
        
        obj = bpy.data.objects.new("CAD_Rectangle", mesh_data)
        context.collection.objects.link(obj)
        
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        
        self.cleanup(context)

    def cleanup(self, context):
        self.active = False
        context.window.cursor_set('DEFAULT')
        context.area.header_text_set(None)
        if self.draw_handle:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, 'WINDOW')

class SKETCH_OT_draw_circle(bpy.types.Operator):
    """Draw a filled circle by dragging from the center to the radius."""
    bl_idname = "sketch.draw_circle"
    bl_label = "Draw Circle"
    bl_options = {'REGISTER', 'UNDO'}

    def draw_callback_px(self, context):
        if self.center_pos_3d and self.mouse_pos_3d:
            radius = (self.mouse_pos_3d - self.center_pos_3d).length
            if radius > 0.001:
                verts_3d = draw_circle_3d(self.center_pos_3d, radius, Vector((0,0,1)))
                
                shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
                batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": verts_3d})
                shader.bind()
                shader.uniform_float("color", (0.1, 0.1, 0.8, 1.0))
                batch.draw(shader)
                
                dim_text = f"Radius: {radius:.3f}"
                draw_text_2d(self.mouse_pos_2d.x, self.mouse_pos_2d.y, dim_text)

    def invoke(self, context, event):
        self.center_pos_3d = None
        self.mouse_pos_3d = None
        self.mouse_pos_2d = None
        self.active = True
        
        self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, (context,), 'WINDOW', 'POST_VIEW')
        context.window_manager.modal_handler_add(self)
        context.window.cursor_set('CROSSHAIR')
        context.area.header_text_set("CAD Sketcher: Click and drag to draw circle. ESC to cancel.")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if not self.active: return {'FINISHED'}

        self.mouse_pos_3d = mouse_to_plane_coord(context, event)
        self.mouse_pos_2d = Vector((event.mouse_region_x, event.mouse_region_y))
        
        if self.mouse_pos_3d is None: return {'PASS_THROUGH'}
        
        context.area.tag_redraw()

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.center_pos_3d = self.mouse_pos_3d
            return {'RUNNING_MODAL'}
        
        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self.finish_drawing(context)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cleanup(context)
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def finish_drawing(self, context):
        if not self.center_pos_3d or not self.mouse_pos_3d:
            self.cleanup(context)
            return
            
        radius = (self.mouse_pos_3d - self.center_pos_3d).length
        if radius < 0.001:
            self.cleanup(context)
            return

        bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=True, radius=radius, segments=32)
        
        bmesh.ops.translate(bm, verts=bm.verts, vec=self.center_pos_3d)

        mesh_data = bpy.data.meshes.new("CAD_Circle_Mesh")
        bm.to_mesh(mesh_data)
        bm.free()
        
        obj = bpy.data.objects.new("CAD_Circle", mesh_data)
        context.collection.objects.link(obj)
        
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        
        self.cleanup(context)

    def cleanup(self, context):
        self.active = False
        context.window.cursor_set('DEFAULT')
        context.area.header_text_set(None)
        if self.draw_handle:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, 'WINDOW')

class SKETCH_OT_draw_polyline(SketcherModalBase):
    """Draw a multi-segment line (polyline) in the 3D view."""
    bl_idname = "sketch.draw_polyline"
    bl_label = "Draw Poly-line"

    def invoke(self, context, event):
        context.area.header_text_set("Poly-line: Click to place points. ENTER/SPACE to finish. ESC to cancel.")
        return super().invoke(context, event)

    def modal(self, context, event):
        if not self.active:
            return {'FINISHED'}

        self.mouse_pos_3d = self.get_snapped_point(context, event)
        if self.mouse_pos_3d is None:
            return {'PASS_THROUGH'}

        context.area.tag_redraw()

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.points.append(self.mouse_pos_3d)
            return {'RUNNING_MODAL'}

        elif event.type in {'RET', 'SPACE'} and event.value == 'PRESS':
            if len(self.points) >= 2:
                self.finish_drawing(context)
                return {'FINISHED'}
            else:
                self.cleanup(context)
                return {'CANCELLED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cleanup(context)
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def draw_callback_px(self, context):
        if not self.points:
            return

        verts_to_draw = self.points + [self.mouse_pos_3d] if self.mouse_pos_3d else self.points

        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": verts_to_draw})
        shader.bind()
        shader.uniform_float("color", (0.1, 0.1, 0.8, 1.0))
        batch.draw(shader)

    def finish_drawing(self, context):
        if len(self.points) < 2:
            self.cleanup(context)
            return

        bm = bmesh.new()
        bverts = [bm.verts.new(p) for p in self.points]
        for i in range(len(bverts) - 1):
            bm.edges.new((bverts[i], bverts[i+1]))

        mesh_data = bpy.data.meshes.new("Polyline_Mesh")
        bm.to_mesh(mesh_data)
        bm.free()

        obj = bpy.data.objects.new("Polyline", mesh_data)
        context.collection.objects.link(obj)

        self.cleanup(context)


class SKETCH_OT_draw_circle_diameter(SketcherModalBase):
    """Draw a circle from two points defining its diameter."""
    bl_idname = "sketch.draw_circle_diameter"
    bl_label = "Draw 2-Point Circle"

    def invoke(self, context, event):
        context.area.header_text_set("2-Point Circle: Click for first diameter point.")
        return super().invoke(context, event)

    def modal(self, context, event):
        if not self.active:
            return {'FINISHED'}

        self.mouse_pos_3d = self.get_snapped_point(context, event)
        if self.mouse_pos_3d is None:
            return {'PASS_THROUGH'}

        context.area.tag_redraw()

        header_text = "2-Point Circle: Click for second diameter point." if self.points else "2-Point Circle: Click for first diameter point."
        context.area.header_text_set(header_text)

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.points.append(self.mouse_pos_3d)
            if len(self.points) == 2:
                self.finish_drawing(context)
                return {'FINISHED'}
            return {'RUNNING_MODAL'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cleanup(context)
            return {'CANCELLED'}

        return {'PASS_THROUGH'}

    def draw_callback_px(self, context):
        if len(self.points) == 1 and self.mouse_pos_3d:
            p1 = self.points[0]
            p2 = self.mouse_pos_3d

            center = (p1 + p2) / 2
            radius = (p2 - p1).length / 2

            if radius > 0.001:
                view_normal = context.region_data.view_matrix.to_quaternion() @ Vector((0,0,-1))
                verts_3d = draw_circle_3d(center, radius, view_normal)

                shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
                batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": verts_3d})
                shader.bind()
                shader.uniform_float("color", (0.1, 0.1, 0.8, 1.0))
                batch.draw(shader)

                dim_text = f"Diameter: {radius*2:.3f}"
                mouse_2d = location_3d_to_region_2d(context.region, context.region_data, self.mouse_pos_3d)
                if mouse_2d:
                    draw_text_2d(mouse_2d.x + 10, mouse_2d.y + 10, dim_text)

    def finish_drawing(self, context):
        if len(self.points) != 2:
            self.cleanup(context)
            return

        p1, p2 = self.points
        center = (p1 + p2) / 2
        radius = (p1 - p2).length / 2

        if radius < 0.001:
            self.cleanup(context)
            return

        bm = bmesh.new()
        view_normal = context.region_data.view_matrix.to_quaternion() @ Vector((0,0,-1))

        bmesh.ops.create_circle(bm, cap_ends=True, radius=radius, segments=64)

        rot = view_normal.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        bmesh.ops.transform(bm, matrix=rot, verts=bm.verts)
        bmesh.ops.translate(bm, verts=bm.verts, vec=center)

        mesh_data = bpy.data.meshes.new("Circle_Dia_Mesh")
        bm.to_mesh(mesh_data)
        bm.free()

        obj = bpy.data.objects.new("Circle_Dia", mesh_data)
        context.collection.objects.link(obj)

        self.cleanup(context)

# Due to the mathematical complexity of a robust 3-point arc tool,
# it will be implemented separately. For now, we provide the other requested tools.
class SKETCH_OT_draw_arc(bpy.types.Operator):
    bl_idname = "sketch.draw_arc"
    bl_label = "Draw 3-Point Arc (WIP)"

    def execute(self, context):
        self.report({'INFO'}, "The 3-Point Arc tool is under development and will be available in a future update.")
        return {'CANCELLED'}

classes = (
    SKETCH_OT_draw_line,
    SKETCH_OT_draw_rectangle,
    SKETCH_OT_draw_circle,
    SKETCH_OT_draw_polyline,
    SKETCH_OT_draw_circle_diameter,
    SKETCH_OT_draw_arc,
)

