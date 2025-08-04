# --- File: operators/op_3d.py ---
import bpy
import bmesh
import math

class MESH_OT_create_hole(bpy.types.Operator):
    """Creates a hole (simple, counterbore, or countersink) at the 3D cursor."""
    bl_idname = "mesh.create_hole"
    bl_label = "Create Hole"
    bl_options = {'REGISTER', 'UNDO'}

    hole_type: bpy.props.EnumProperty(name="Type", items=[('SIMPLE', "Simple", ""), ('COUNTERBORE', "Counterbore", ""), ('COUNTERSINK', "Countersink", "")], default='SIMPLE')
    diameter: bpy.props.FloatProperty(name="Diameter", default=0.005, min=0.0001, subtype='DISTANCE')
    depth: bpy.props.FloatProperty(name="Depth", default=0.01, min=0.0001, subtype='DISTANCE')
    cb_diameter: bpy.props.FloatProperty(name="CB Diameter", default=0.01, min=0.0001, subtype='DISTANCE')
    cb_depth: bpy.props.FloatProperty(name="CB Depth", default=0.002, min=0.0001, subtype='DISTANCE')
    cs_angle: bpy.props.FloatProperty(name="CS Angle", default=90.0, min=1.0, max=179.0, subtype='ANGLE')

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, "hole_type")
        layout.prop(self, "diameter")
        layout.prop(self, "depth")
        if self.hole_type == 'COUNTERBORE':
            layout.separator()
            layout.prop(self, "cb_diameter")
            layout.prop(self, "cb_depth")
        elif self.hole_type == 'COUNTERSINK':
            layout.separator()
            layout.prop(self, "cs_angle")

    def execute(self, context):
        target_obj = context.active_object
        cursor_loc = context.scene.cursor.location
        bm = bmesh.new()

        # Main hole
        cone_main = bmesh.ops.create_cone(bm, cap_ends=True, segments=64, radius1=self.diameter / 2, radius2=self.diameter / 2, depth=self.depth)
        bmesh.ops.translate(bm, verts=cone_main['verts'], vec=(0, 0, -self.depth / 2))

        if self.hole_type == 'COUNTERBORE':
            if self.cb_diameter <= self.diameter or self.cb_depth <= 0:
                self.report({'ERROR'}, "Counterbore dimensions must be larger than hole.")
                return {'CANCELLED'}
            cone_cb = bmesh.ops.create_cone(bm, cap_ends=True, segments=64, radius1=self.cb_diameter / 2, radius2=self.cb_diameter / 2, depth=self.cb_depth)
            bmesh.ops.translate(bm, verts=cone_cb['verts'], vec=(0, 0, self.cb_depth / 2))

        elif self.hole_type == 'COUNTERSINK':
            cs_radius = self.diameter / 2
            cs_depth = cs_radius / math.tan(math.radians(self.cs_angle / 2))
            cone_cs = bmesh.ops.create_cone(bm, cap_ends=True, segments=64, radius1=cs_radius, radius2=0, depth=cs_depth)
            bmesh.ops.translate(bm, verts=cone_cs['verts'], vec=(0, 0, cs_depth / 2))
        
        cutter_mesh = bpy.data.meshes.new("HoleCutter_Mesh")
        bm.to_mesh(cutter_mesh)
        bm.free()
        cutter_obj = bpy.data.objects.new("HoleCutter", cutter_mesh)
        cutter_obj.location = cursor_loc
        context.collection.objects.link(cutter_obj)
        mod = target_obj.modifiers.new(name="HoleBoolean", type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = cutter_obj
        mod.solver = 'FAST'
        bpy.ops.object.select_all(action='DESELECT')
        target_obj.select_set(True)
        context.view_layer.objects.active = target_obj
        bpy.ops.object.modifier_apply({"modifier": mod.name})
        bpy.data.objects.remove(cutter_obj, do_unlink=True)
        bpy.data.meshes.remove(cutter_mesh)

        # Add to feature tree
        feature = target_obj.object_cad_settings.feature_tree.add()
        feature.name = "Create Hole"
        feature.type = 'CREATE_HOLE'
        feature.hole_type = self.hole_type
        feature.hole_diameter = self.diameter
        feature.hole_depth = self.depth
        feature.hole_cb_diameter = self.cb_diameter
        feature.hole_cb_depth = self.cb_depth
        feature.hole_cs_angle = self.cs_angle

        return {'FINISHED'}


class MESH_OT_create_gear(bpy.types.Operator):
    """Creates a parametric involute spur gear."""
    bl_idname = "mesh.create_gear"
    bl_label = "Create Spur Gear"
    bl_options = {'REGISTER', 'UNDO'}

    module: bpy.props.FloatProperty(name="Module", default=0.1, min=0.01)
    num_teeth: bpy.props.IntProperty(name="Number of Teeth", default=12, min=3)
    width: bpy.props.FloatProperty(name="Width", default=0.2, min=0.001, subtype='DISTANCE')

    def execute(self, context):
        pressure_angle = math.radians(20)
        pitch_diameter = self.module * self.num_teeth
        pitch_radius = pitch_diameter / 2
        base_radius = pitch_radius * math.cos(pressure_angle)
        addendum = self.module
        dedendum = 1.25 * self.module
        outer_radius = pitch_radius + addendum
        root_radius = pitch_radius - dedendum
        if base_radius > root_radius:
            root_radius = base_radius
        bm = bmesh.new()
        verts = []
        tooth_angle = 2 * math.pi / self.num_teeth
        for i in range(self.num_teeth * 4):
            tooth_i = i // 4
            part_i = i % 4
            radius = root_radius if part_i == 0 or part_i == 3 else outer_radius
            angle_rad = (tooth_i / self.num_teeth) * 2 * math.pi
            angle_rad += ((part_i - 1.5) / 2) * (tooth_angle * 0.5)
            x = radius * math.cos(angle_rad)
            y = radius * math.sin(angle_rad)
            verts.append(bm.verts.new((x, y, 0)))
        bm.faces.new(verts)
        geom = bmesh.ops.extrude_face_region(bm, geom=bm.faces)
        bmesh.ops.translate(bm, verts=[v for v in geom['geom'] if isinstance(v, bmesh.types.BMVert)], vec=(0, 0, self.width))
        gear_mesh = bpy.data.meshes.new("SpurGear_Mesh")
        bm.to_mesh(gear_mesh)
        bm.free()
        gear_obj = bpy.data.objects.new("SpurGear", gear_mesh)
        context.collection.objects.link(gear_obj)
        context.view_layer.objects.active = gear_obj
        gear_obj.select_set(True)

        # Add to feature tree
        feature = gear_obj.object_cad_settings.feature_tree.add()
        feature.name = "Create Gear"
        feature.type = 'CREATE_GEAR'
        feature.gear_module = self.module
        feature.gear_num_teeth = self.num_teeth
        feature.gear_width = self.width

        return {'FINISHED'}


class MESH_OT_simple_extrude(bpy.types.Operator):
    """Extrudes the selected faces of the active object."""
    bl_idname = "mesh.simple_extrude"
    bl_label = "Extrude"
    bl_options = {'REGISTER', 'UNDO'}

    extrude_depth: bpy.props.FloatProperty(name="Depth", default=1.0, subtype='DISTANCE')

    def execute(self, context):
        if context.active_object and context.active_object.type == 'MESH':
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, self.extrude_depth)})
            bpy.ops.object.mode_set(mode='OBJECT')

            # Add to feature tree
            feature = context.active_object.object_cad_settings.feature_tree.add()
            feature.name = "Extrude"
            feature.type = 'EXTRUDE'
            feature.extrude_depth = self.extrude_depth
        else:
            self.report({'WARNING'}, "No active mesh object selected.")
            return {'CANCELLED'}
        return {'FINISHED'}



class MESH_OT_bevel_edges(bpy.types.Operator):
    """Bevels the selected edges of the active object."""
    bl_idname = "mesh.bevel_edges"
    bl_label = "Bevel Edges"
    bl_options = {'REGISTER', 'UNDO'}

    bevel_amount: bpy.props.FloatProperty(name="Amount", default=0.2, subtype='DISTANCE')
    bevel_segments: bpy.props.IntProperty(name="Segments", default=4, min=1)

    def execute(self, context):
        if context.active_object and context.active_object.type == 'MESH':
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.bevel(offset=self.bevel_amount, segments=self.bevel_segments)
            bpy.ops.object.mode_set(mode='OBJECT')

            # Add to feature tree
            feature = context.active_object.object_cad_settings.feature_tree.add()
            feature.name = "Bevel"
            feature.type = 'BEVEL'
            feature.bevel_amount = self.bevel_amount
            feature.bevel_segments = self.bevel_segments
        else:
            self.report({'WARNING'}, "No active mesh object selected.")
            return {'CANCELLED'}
        return {'FINISHED'}

class MESH_OT_inner_radius(bpy.types.Operator):
    """Creates a hollow object with a specified wall thickness."""
    bl_idname = "mesh.inner_radius"
    bl_label = "Inner Radius"
    bl_options = {'REGISTER', 'UNDO'}

    width: bpy.props.FloatProperty(
        name="Wall Thickness (X)",
        description="Wall thickness on the X-axis",
        default=0.1,
        min=0.001,
        subtype='DISTANCE'
    )

    length: bpy.props.FloatProperty(
        name="Wall Thickness (Y)",
        description="Wall thickness on the Y-axis",
        default=0.1,
        min=0.001,
        subtype='DISTANCE'
    )

    height: bpy.props.FloatProperty(
        name="Wall Thickness (Z)",
        description="Wall thickness on the Z-axis",
        default=0.1,
        min=0.001,
        subtype='DISTANCE'
    )

    offset_x: bpy.props.FloatProperty(
        name="Offset X (Left/Right)",
        description="Move the inner hole left or right",
        default=0.0,
        subtype='DISTANCE'
    )

    offset_y: bpy.props.FloatProperty(
        name="Offset Y (Front/Back)",
        description="Move the inner hole front or back",
        default=0.0,
        subtype='DISTANCE'
    )

    offset_z: bpy.props.FloatProperty(
        name="Offset Z (Up/Down)",
        description="Move the inner hole up or down",
        default=0.0,
        subtype='DISTANCE'
    )

    rotation: bpy.props.FloatProperty(
        name="Rotation",
        description="Rotation of the inner hole around the Z-axis",
        default=0.0,
        subtype='ANGLE',
        unit='ROTATION'
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        target_obj = context.active_object
        
        # Apply scale of target object to avoid issues with dimensions
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        # Duplicate the object to create the cutter
        bpy.ops.object.duplicate()
        cutter_obj = context.active_object

        # Move the cutter
        cutter_obj.location.x += self.offset_x
        cutter_obj.location.y += self.offset_y
        cutter_obj.location.z += self.offset_z

        # Rotate the cutter
        cutter_obj.rotation_euler.z += self.rotation

        # Calculate scale factors from wall thickness
        dims = target_obj.dimensions
        
        if dims.x == 0 or dims.y == 0 or dims.z == 0:
            self.report({'ERROR'}, "Object has zero dimension on one or more axes.")
            bpy.data.objects.remove(cutter_obj, do_unlink=True)
            return {'CANCELLED'}
            
        scale_x = (dims.x - 2 * self.width) / dims.x if dims.x != 0 else 1
        scale_y = (dims.y - 2 * self.length) / dims.y if dims.y != 0 else 1
        scale_z = (dims.z - 2 * self.height) / dims.z if dims.z != 0 else 1
        
        if scale_x <= 0 or scale_y <= 0 or scale_z <= 0:
            self.report({'ERROR'}, "Wall thickness is too large for the object dimensions.")
            bpy.data.objects.remove(cutter_obj, do_unlink=True)
            return {'CANCELLED'}

        # Scale the cutter
        bpy.ops.transform.resize(value=(scale_x, scale_y, scale_z))

        # Add boolean modifier to the original object
        bpy.context.view_layer.objects.active = target_obj
        mod = target_obj.modifiers.new(name="InnerRadiusBoolean", type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = cutter_obj
        mod.solver = 'FAST'

        # Apply the modifier
        bpy.ops.object.modifier_apply(modifier=mod.name)

        # Clean up the cutter object
        bpy.data.objects.remove(cutter_obj, do_unlink=True)

        # Add to feature tree
        feature = target_obj.object_cad_settings.feature_tree.add()
        feature.name = "Inner Radius"
        feature.type = 'INNER_RADIUS'
        feature.inner_radius_width = self.width
        feature.inner_radius_length = self.length
        feature.inner_radius_height = self.height
        feature.inner_radius_offset_x = self.offset_x
        feature.inner_radius_offset_y = self.offset_y
        feature.inner_radius_offset_z = self.offset_z
        feature.inner_radius_rotation = self.rotation

        return {'FINISHED'}

classes = (
    MESH_OT_create_hole,
    MESH_OT_create_gear,
    MESH_OT_simple_extrude,
    MESH_OT_bevel_edges,
    MESH_OT_inner_radius,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
