# #############################################################################
# --- File: utils.py ---
# #############################################################################
import bpy
import blf
import math
from mathutils import Vector
from mathutils.geometry import intersect_line_plane
from gpu_extras.batch import batch_for_shader
from bpy_extras.view3d_utils import region_2d_to_origin_3d, region_2d_to_vector_3d, location_3d_to_region_2d

def mouse_to_plane_coord(context, event, plane_co=(0, 0, 0), plane_no=(0, 0, 1)):
    """ Converts a 2D mouse coordinate to a 3D point on a plane. """
    region = context.region
    rv3d = context.region_data
    coord = event.mouse_region_x, event.mouse_region_y
    ray_origin = region_2d_to_origin_3d(region, rv3d, coord)
    ray_vector = region_2d_to_vector_3d(region, rv3d, coord)
    intersection_point = intersect_line_plane(ray_origin, ray_origin + ray_vector, plane_co, plane_no)
    return intersection_point

def draw_circle_3d(position, radius, normal, segments=32):
    """ Helper function to generate vertices for a 3D circle for drawing. """
    coords = []
    if normal.length == 0: return coords
    
    q = Vector((0,0,1)).rotation_difference(normal)
    
    for i in range(segments + 1):
        angle = (i / segments) * 2 * math.pi
        v = Vector((math.cos(angle) * radius, math.sin(angle) * radius, 0))
        v.rotate(q)
        coords.append(position + v)
    return coords

def draw_text_2d(x, y, text, size=14, color=(1.0, 1.0, 1.0, 1.0)):
    """ Draws text in the 2D region of the viewport. """
    font_id = 0
    blf.position(font_id, x + 15, y + 15, 0)
    blf.size(font_id, size)
    blf.color(font_id, *color)
    blf.draw(font_id, text)