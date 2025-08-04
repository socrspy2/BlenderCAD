# --- File: properties.py ---
import bpy

# --- Update functions for Reference Images ---
def update_ref_image_property(self, context):
    """Generic update function for reference image properties (size, offset, opacity)."""
    if self.empty_ref:
        self.empty_ref.empty_display_size = self.size
        self.empty_ref.location.x = self.offset_x
        self.empty_ref.location.y = self.offset_y
        self.empty_ref.color[3] = self.opacity # Use alpha channel of color for opacity

def update_ref_image_visibility(self, context):
    """Toggles the visibility of all reference image empties."""
    settings = context.scene.scene_cad_settings
    view_keys = ['top', 'front', 'right', 'bottom', 'back', 'left']
    for view_key in view_keys:
        image_settings = getattr(settings, f"{view_key}_image", None)
        if image_settings and image_settings.empty_ref:
            image_settings.empty_ref.hide_viewport = not settings.show_ref_sketches


class ReferenceImageSettings(bpy.types.PropertyGroup):
    """Stores settings for a single reference image."""
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    empty_ref: bpy.props.PointerProperty(name="Empty Reference", type=bpy.types.Object)
    size: bpy.props.FloatProperty(name="Size", default=5.0, min=0.01, subtype='DISTANCE', update=update_ref_image_property)
    offset_x: bpy.props.FloatProperty(name="X Offset", default=0.0, subtype='DISTANCE', update=update_ref_image_property)
    offset_y: bpy.props.FloatProperty(name="Y Offset", default=0.0, subtype='DISTANCE', update=update_ref_image_property)
    opacity: bpy.props.FloatProperty(name="Opacity", default=0.5, min=0.0, max=1.0, subtype='FACTOR', update=update_ref_image_property)


def update_view_pan(self, context):
    """ Pans the 3D view based on the slider values. """
    space = context.space_data
    if space.type == 'VIEW_3D':
        region_3d = space.region_3d
        view_matrix = region_3d.view_matrix.inverted()
        x_axis = view_matrix.col[0].xyz
        y_axis = view_matrix.col[1].xyz
        new_location = self.pan_origin + (x_axis * self.pan_x) + (y_axis * self.pan_y)
        region_3d.view_location = new_location

def update_units_and_grid(self, context):
    """ Updates Blender's scene and viewport based on addon settings. """
    if not context.scene:
        return
        
    scene = context.scene
    settings = scene.scene_cad_settings

    if settings.unit_system == 'METRIC':
        scene.unit_settings.system = 'METRIC'
        scene.unit_settings.length_unit = settings.metric_unit
    elif settings.unit_system == 'IMPERIAL':
        scene.unit_settings.system = 'IMPERIAL'
        scene.unit_settings.length_unit = 'INCHES'

    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.overlay.show_floor = settings.show_grid
                    space.overlay.grid_scale = settings.grid_spacing

                    # Adjust subdivisions to keep the grid visually clean at small scales
                    if settings.grid_spacing < 0.01: # e.g., < 1cm
                        space.overlay.grid_subdivisions = 1
                    elif settings.grid_spacing < 0.1: # e.g., < 10cm
                        space.overlay.grid_subdivisions = 2
                    else:
                        space.overlay.grid_subdivisions = 10

                    space.tag_redraw()


class CADFeature(bpy.types.PropertyGroup):
    """Base class for a single feature in the feature tree."""
    name: bpy.props.StringProperty(name="Feature Name")
    type: bpy.props.EnumProperty(
        name="Feature Type",
        items=[
            ('EXTRUDE', "Extrude", "Extrude operation"),
            ('BEVEL', "Bevel", "Bevel operation"),
            # Add other feature types here in the future
        ]
    )

class ExtrudeFeature(CADFeature):
    """Properties for an extrude feature."""
    extrude_depth: bpy.props.FloatProperty(name="Depth", default=1.0, subtype='DISTANCE')

class BevelFeature(CADFeature):
    """Properties for a bevel feature."""
    bevel_amount: bpy.props.FloatProperty(name="Amount", default=0.2, subtype='DISTANCE')
    bevel_segments: bpy.props.IntProperty(name="Segments", default=4, min=1)


class ObjectCADSettings(bpy.types.PropertyGroup):
    """Stores object-specific settings for the CAD addon, primarily the feature tree."""
    feature_tree: bpy.props.CollectionProperty(type=CADFeature)
    active_feature_index: bpy.props.IntProperty()
    expand_feature_tree: bpy.props.BoolProperty(default=True)

class SceneCADSettings(bpy.types.PropertyGroup):
    """Stores scene-level settings for the CAD addon."""
    # --- UI Expansion States ---
    expand_view_navigator: bpy.props.BoolProperty(default=True)
    expand_reference_sketches: bpy.props.BoolProperty(default=False)
    expand_units_and_grid: bpy.props.BoolProperty(default=False)
    expand_2d_sketching: bpy.props.BoolProperty(default=False)
    expand_3d_operations: bpy.props.BoolProperty(default=False)

    pan_x: bpy.props.FloatProperty(name="Pan Left/Right", default=0.0, update=update_view_pan)
    pan_y: bpy.props.FloatProperty(name="Pan Up/Down", default=0.0, update=update_view_pan)
    pan_origin: bpy.props.FloatVectorProperty(name="Pan Origin", subtype='TRANSLATION')
    
    use_grid_snap: bpy.props.BoolProperty(name="Grid Snap", default=False)
    use_vertex_snap: bpy.props.BoolProperty(name="Vertex Snap", default=True)
    use_fill: bpy.props.BoolProperty(name="Auto Fill",description="Automatically creates a face",default=False)

    unit_system: bpy.props.EnumProperty(name="Unit System", items=[('METRIC', "Metric", ""), ('IMPERIAL', "Imperial", "")], default='METRIC', update=update_units_and_grid)
    metric_unit: bpy.props.EnumProperty(name="Metric Unit", items=[('METERS', "Meters", ""), ('CENTIMETERS', "Centimeters", ""), ('MILLIMETERS', "Millimeters", "")], default='MILLIMETERS', update=update_units_and_grid)
    show_grid: bpy.props.BoolProperty(name="Show Grid", default=True, update=update_units_and_grid)
    grid_spacing: bpy.props.FloatProperty(name="Grid Spacing", default=0.01, min=0.0001, subtype='DISTANCE', update=update_units_and_grid)

    show_grid_dimensions: bpy.props.BoolProperty(name="Show Dimensions", default=False, description="Display grid scale markings in the viewport", update=update_units_and_grid)
    grid_dimension_font_size: bpy.props.IntProperty(name="Font Size", default=12, min=8, max=72, description="Font size for the grid dimensions", update=update_units_and_grid)
    grid_dimension_color: bpy.props.FloatVectorProperty(name="Color", subtype='COLOR', default=(1.0, 1.0, 1.0), min=0.0, max=1.0, description="Color for the grid dimensions", update=update_units_and_grid)

    show_ref_sketches: bpy.props.BoolProperty(name="Show/Hide Sketches", default=True, update=update_ref_image_visibility)
    top_image: bpy.props.PointerProperty(type=ReferenceImageSettings)
    front_image: bpy.props.PointerProperty(type=ReferenceImageSettings)
    right_image: bpy.props.PointerProperty(type=ReferenceImageSettings)
    bottom_image: bpy.props.PointerProperty(type=ReferenceImageSettings)
    back_image: bpy.props.PointerProperty(type=ReferenceImageSettings)
    left_image: bpy.props.PointerProperty(type=ReferenceImageSettings)


classes = (
    ReferenceImageSettings,
    CADFeature,
    ExtrudeFeature,
    BevelFeature,
    ObjectCADSettings,
    SceneCADSettings,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.object_cad_settings = bpy.props.PointerProperty(type=ObjectCADSettings)
    bpy.types.Scene.scene_cad_settings = bpy.props.PointerProperty(type=SceneCADSettings)

def unregister():
    del bpy.types.Scene.scene_cad_settings
    del bpy.types.Object.object_cad_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
