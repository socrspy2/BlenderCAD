import bpy
import blf
import gpu
from mathutils import Vector
from bpy_extras.view3d_utils import region_2d_to_location_3d

def get_view_orientation(context):
    """Returns the orientation of the 3D view, e.g., 'TOP', 'FRONT', 'PERSP', etc."""
    region_3d = context.space_data.region_3d
    view_quat = region_3d.view_rotation

    # These vectors define the standard view orientations
    view_vectors = {
        'TOP': Vector((0, 0, 1)),
        'BOTTOM': Vector((0, 0, -1)),
        'FRONT': Vector((0, -1, 0)),
        'BACK': Vector((0, 1, 0)),
        'RIGHT': Vector((1, 0, 0)),
        'LEFT': Vector((-1, 0, 0)),
    }

    # The camera's forward vector is the Z-axis of its rotation
    forward_vector = view_quat @ Vector((0, 0, -1))

    for name, vec in view_vectors.items():
        if forward_vector.dot(vec) > 0.99:
            return name

    return 'PERSP' # If not aligned with any axis, assume perspective/user view

def draw_grid_dimensions_callback(context):
    """Draws dimension labels on the grid in the 3D viewport."""
    settings = context.scene.cad_tool_settings
    if not settings.show_grid_dimensions:
        return

    space = context.space_data
    if space.type != 'VIEW_3D' or not space.overlay.show_floor:
        return

    # Only draw in orthographic, axis-aligned views for clarity
    if space.region_3d.view_perspective != 'ORTHO':
        return

    orientation = get_view_orientation(context)
    if orientation == 'PERSP':
        return

    # --- Setup Drawing ---
    font_id = 0  # Default font
    blf.size(font_id, settings.grid_dimension_font_size)
    # Set the color with alpha
    color = (*settings.grid_dimension_color, 1.0)
    blf.color(font_id, *color)

    region = context.region
    region_3d = space.region_3d

    # Get visible range
    view_center_3d = region_2d_to_location_3d(region, region_3d, region.width / 2, region.height / 2, region_3d.view_location)
    zoom_factor = region_3d.view_distance * 0.2

    grid_scale = space.overlay.grid_scale
    if grid_scale <= 0: return

    # --- Draw Labels ---
    def draw_label(text, coord_3d):
        coord_2d = bpy.context.region_data.view3d_to_region_2d(region, coord_3d, default=None)
        if coord_2d is None: return
        blf.position(font_id, coord_2d.x, coord_2d.y, 0)
        blf.draw(font_id, text)

    # Determine which axes to label based on orientation
    if orientation in ['TOP', 'BOTTOM']:
        x_axis, y_axis = 0, 1
    elif orientation in ['FRONT', 'BACK']:
        x_axis, y_axis = 0, 2
    elif orientation in ['LEFT', 'RIGHT']:
        x_axis, y_axis = 1, 2
    else:
        return

    # Draw labels along the horizontal axis
    for i in range(-50, 51):
        if i == 0: continue
        pos = i * grid_scale
        coord = Vector((0,0,0))
        coord[x_axis] = pos
        label_text = bpy.utils.units.to_string_pretty(pos, context.scene.unit_settings)
        draw_label(label_text, coord)

    # Draw labels along the vertical axis
    for i in range(-50, 51):
        if i == 0: continue
        pos = i * grid_scale
        coord = Vector((0,0,0))
        coord[y_axis] = pos
        label_text = bpy.utils.units.to_string_pretty(pos, context.scene.unit_settings)
        draw_label(label_text, coord)


# --- Registration ---
draw_handler = None

def register():
    """Adds the draw handler to the 3D view."""
    global draw_handler
    if draw_handler is None:
        draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            draw_grid_dimensions_callback, (bpy.context,), 'WINDOW', 'POST_PIXEL'
        )

def unregister():
    """Removes the draw handler from the 3D view."""
    global draw_handler
    if draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(draw_handler, 'WINDOW')
        draw_handler = None
