# --- File: operators/sketch_tools.py ---
import bpy
import bmesh
import gpu
import blf
import math
from mathutils import Vector
from gpu_extras.batch import batch_for_shader
from bpy_extras.view3d_utils import location_3d_to_region_2d
from ..utils import mouse_to_plane_coord, draw_circle_3d, draw_text_2d # Assuming these are defined in your utils.py

class SketcherModalBase(bpy.types.Operator):
    """Base class for modal sketching operators."""
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        self.active = True
        # Add draw handler for post-view drawing (3D space)
        # Corrected: bpy.types.SpaceView3D (capital D)
        self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, (context,), 'WINDOW', 'POST_VIEW')
        # Add modal handler to capture events
        context.window_manager.modal_handler_add(self)
        # Temporarily disabled cursor set/reset due to potential errors in some Blender versions
        # context.window.cursor_set('CROSSHAIR')
        return {'RUNNING_MODAL'}

    def cleanup(self, context):
        """Clean up resources and reset UI."""
        # context.window.cursor_set('DEFAULT') # Temporarily disabled
        context.area.header_text_set(None) # Clear header text
        if self.draw_handle:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, 'WINDOW')
        self.active = False
        # Reset state variables for the next invocation
        self.points = []
        self.current_blender_object = None
        self.is_first_point = True
        self.is_drawing_polyline = False

    def get_snapped_point(self, context, event):
        """Calculates the 3D mouse position with snapping (vertex and grid)."""
        settings = context.scene.scene_cad_settings # Assuming a custom scene property group for CAD settings
        snapped_vertex_pos = None

        # Get raw 3D mouse position on the working plane
        temp_mouse_pos = mouse_to_plane_coord(context, event)
        if temp_mouse_pos is None:
            return None, None # Mouse not over 3D view or plane not defined

        # Vertex Snapping
        if settings.use_vertex_snap:
            snap_threshold_px = 10 # Pixels threshold for snapping
            best_dist_sq = snap_threshold_px**2 # Squared distance for performance
            depsgraph = context.evaluated_depsgraph_get() # Get dependency graph for evaluated mesh data

            # Iterate visible mesh objects to find snap candidates
            for obj in context.visible_objects:
                if obj.type == 'MESH':
                    world_matrix = obj.matrix_world # Object's world transformation
                    mesh = obj.evaluated_get(depsgraph).to_mesh() # Get mesh data (evaluated for modifiers)
                    # Iterate vertices of the mesh
                    for v in mesh.vertices:
                        v_world = world_matrix @ v.co # Vertex position in world space
                        # Convert 3D world position to 2D screen position
                        v_2d = location_3d_to_region_2d(context.region, context.region_data, v_world)
                        if v_2d:
                            # Calculate squared distance from mouse to vertex on screen
                            dist_sq = (v_2d.x - event.mouse_region_x)**2 + (v_2d.y - event.mouse_region_y)**2
                            if dist_sq < best_dist_sq:
                                best_dist_sq = dist_sq
                                snapped_vertex_pos = v_world # Store the snapped 3D position
                    # mesh.free_copy() # Free the temporary mesh copy - REMOVED: 'Mesh' object has no attribute 'free_copy' in Blender 4.x

            if snapped_vertex_pos:
                # If a vertex was snapped, return its world position as both actual and snapped
                return snapped_vertex_pos, snapped_vertex_pos

        # Grid Snapping (applies if no vertex snap occurred or if vertex snap is off)
        if settings.use_grid_snap:
            scale = context.space_data.overlay.grid_scale # Current grid scale
            # Round coordinates to the nearest grid increment
            temp_mouse_pos.x = round(temp_mouse_pos.x / scale) * scale
            temp_mouse_pos.y = round(temp_mouse_pos.y / scale) * scale
            temp_mouse_pos.z = round(temp_mouse_pos.z / scale) * scale

        return temp_mouse_pos, snapped_vertex_pos

class SKETCH_OT_draw_line(SketcherModalBase):
    bl_idname = "sketch.draw_line"
    bl_label = "Draw Line"
    bl_description = "Draws lines and polylines with snapping."

    def invoke(self, context, event):
        # Initialize state for line/polyline drawing
        self.points = [] # Stores 3D coordinates of the polyline vertices
        self.mouse_pos_3d = None # Current 3D mouse position
        self.snapped_vertex_pos = None # 3D position of snapped vertex, if any
        
        # Drawing batches for GPU rendering
        self.batch_line = None
        self.batch_snap = None
        self.shader = gpu.shader.from_builtin('UNIFORM_COLOR') # Generic shader for uniform color

        # New state variables for continuous drawing logic
        self.current_blender_object = None # The bpy.types.Object we are currently drawing into
        self.is_first_point = True # True if we are waiting for the very first point of a new line/polyline session
        self.is_drawing_polyline = False # True if Shift is held and we are continuously adding segments

        context.area.header_text_set("Line: Click for start point. Hold SHIFT and click to draw polyline. ESC to cancel.")
        return super().invoke(context, event)

    def modal(self, context, event):
        if not self.active:
            return {'FINISHED'}

        # Get current 3D mouse position, potentially snapped
        self.mouse_pos_3d, self.snapped_vertex_pos = self.get_snapped_point(context, event)
        if self.mouse_pos_3d is None:
            # If mouse is outside 3D view, pass through event
            return {'PASS_THROUGH'}
        
        context.area.tag_redraw() # Request a redraw of the 3D view for visual feedback

        # Update drawing batches for the preview
        self._update_drawing_batches(context)

        # Handle user input
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if self.is_first_point:
                # This is the very first point of a new line/polyline session
                self.points.append(self.mouse_pos_3d)
                self.is_first_point = False # No longer the first point
                
                # Ensure we have a NEW object to draw into for a fresh session
                self._create_new_drawing_object(context)
                
                context.area.header_text_set("Line: Click for end point. SHIFT+Click to continue polyline. ESC to cancel.")
                return {'RUNNING_MODAL'}
            else:
                # This is a subsequent point (either end of single line or continuation of polyline)
                prev_point = self.points[-1] # Get the previous point
                self.points.append(self.mouse_pos_3d) # Add the new point

                # Add the new edge segment to the Blender object
                self._add_edge_to_object(context, self.current_blender_object, prev_point, self.mouse_pos_3d)

                if event.shift:
                    # User is holding Shift, continue drawing polyline
                    self.is_drawing_polyline = True
                    context.area.header_text_set(
                        f"Polyline: SHIFT+Click to continue, Click to finish. ESC to cancel. Points: {len(self.points)}"
                    )
                    return {'RUNNING_MODAL'}
                else:
                    # User released Shift or didn't press it for the final click, finish drawing
                    self.is_drawing_polyline = False
                    self._finalise_drawing(context) # Perform final selection and cleanup
                    return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            # Cancel drawing
            self.cleanup(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def _update_drawing_batches(self, context):
        """Updates the GPU drawing batches for line preview and snap indicator."""
        # Snapping indicator
        if self.snapped_vertex_pos:
            # Convert 3D snapped position to 2D screen position for drawing circle
            p_2d = location_3d_to_region_2d(context.region, context.region_data, self.snapped_vertex_pos)
            if p_2d:
                # Draw a circle around the snapped point
                circle_verts = draw_circle_3d(p_2d.to_3d(), 8, Vector((0,0,1)), segments=12)
                self.batch_snap = batch_for_shader(self.shader, 'LINE_STRIP', {"pos": circle_verts})
            else:
                self.batch_snap = None
        else:
            self.batch_snap = None

        # Line/Polyline preview
        if len(self.points) >= 1:
            # Create a list of all points including the current mouse position for preview
            line_verts = list(self.points) # Copy existing points
            line_verts.append(self.mouse_pos_3d) # Add current mouse position as the last point
            # Use LINE_STRIP to connect all points sequentially
            self.batch_line = batch_for_shader(self.shader, 'LINE_STRIP', {"pos": line_verts})
        else:
            self.batch_line = None

    def _create_new_drawing_object(self, context):
        """Always creates a new mesh object for a new drawing session."""
        mesh_data = bpy.data.meshes.new("CAD_Sketch_Mesh")
        obj = bpy.data.objects.new("CAD_Sketch", mesh_data)
        context.collection.objects.link(obj)
        self.current_blender_object = obj
        
        # Ensure the object is in OBJECT mode for bmesh operations
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Select the new object and make it active
        bpy.ops.object.select_all(action='DESELECT')
        self.current_blender_object.select_set(True)
        context.view_layer.objects.active = self.current_blender_object

    def _add_edge_to_object(self, context, obj, p1, p2):
        """Adds an edge between two points to the specified Blender object."""
        if not obj or obj.type != 'MESH':
            print("Error: Target object is not a mesh or does not exist.")
            return

        
        if (p2 - p1).length < 0.0001: 
            return

        # Get bmesh from object data
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        # Find existing vertices or create new ones for p1 and p2
        # Use a small tolerance for finding existing vertices
        v1 = next((v for v in bm.verts if (v.co - p1).length < 0.0001), None)
        v2 = next((v for v in bm.verts if (v.co - p2).length < 0.0001), None)

        if not v1: v1 = bm.verts.new(p1)
        if not v2: v2 = bm.verts.new(p2)

        # Add the edge if it doesn't already exist
        # Check both (v1, v2) and (v2, v1) for existing edges
        if not any(e for e in bm.edges if (e.verts[0] == v1 and e.verts[1] == v2) or (e.verts[0] == v2 and e.verts[1] == v1)):
            bm.edges.new((v1, v2))
        
        # Remove duplicate vertices that might have been created by snapping or small inaccuracies
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
        
        # This operation helps ensure valid geometry, especially for faces, though not strictly needed for just edges
        # bmesh.ops.contextual_create(bm, geom=bm.edges) 
        
        # Write changes back to the mesh data
        bm.to_mesh(obj.data)
        bm.free() # Important: free the bmesh
        obj.data.update() # Update mesh data in Blender

    def _finalise_drawing(self, context):
        """Finalizes the drawing operation, selects the object, and cleans up."""
        if self.current_blender_object:
            # If there are at least 3 points, attempt to close the polyline
            if len(self.points) >= 3:
                first_point = self.points[0]
                last_point = self.points[-1]
                
                # Only add a closing edge if the first and last points are distinct
                # (i.e., the polyline isn't already closed by the last click, or degenerate)
                # Use a small tolerance similar to remove_doubles
                if (last_point - first_point).length > 0.0001: # Use a small epsilon
                    # Add an edge between the last and first point to close the loop
                    self._add_edge_to_object(context, self.current_blender_object, last_point, first_point)

            # Ensure the object is selected and active
            bpy.ops.object.select_all(action='DESELECT')
            self.current_blender_object.select_set(True)
            context.view_layer.objects.active = self.current_blender_object
        self.cleanup(context) # Call base class cleanup

    def draw_callback_px(self, context):
        """Draws the snap indicator and line preview in the 3D view."""
        # Draw snapping indicator
        if self.batch_snap:
            self.shader.bind()
            self.shader.uniform_float("color", (0.1, 0.8, 0.1, 1.0)) # Green color for snap
            self.batch_snap.draw(self.shader)

        # Draw the line/polyline preview
        if self.batch_line:
            self.shader.bind()
            self.shader.uniform_float("color", (0.1, 0.1, 0.8, 1.0)) # Blue color for line
            self.batch_line.draw(self.shader)

# --- Registration ---
classes = (
    SKETCH_OT_draw_line,
    # SKETCH_OT_draw_rectangle, # To be updated
    # SKETCH_OT_draw_circle, # To be updated
    # SKETCH_OT_draw_polyline, # This functionality is now integrated into SKETCH_OT_draw_line
    # SKETCH_OT_draw_circle_diameter, # To be implemented
    # SKETCH_OT_draw_arc, # To be implemented
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
