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
        else:
            self.report({'WARNING'}, "No active mesh object selected.")
            return {'CANCELLED'}
        return {'FINISHED'}

class MESH_OT_offset_edges(bpy.types.Operator):
    """Offsets the selected edges of the active object."""
    bl_idname = "mesh.offset_edges"
    bl_label = "Offset Edges"
    bl_options = {'REGISTER', 'UNDO'}

    offset_distance: bpy.props.FloatProperty(name="Distance", default=0.2, subtype='DISTANCE')

    def execute(self, context):
        if context.active_object and context.active_object.type == 'MESH':
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.offset_edges(geometry_mode='extrude', use_even=True, amount=self.offset_distance)
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            self.report({'WARNING'}, "No active mesh object selected.")
            return {'CANCELLED'}
        return {'FINISHED'}

class MESH_OT_inset_faces(bpy.types.Operator):
    """Insets the selected faces of the active object."""
    bl_idname = "mesh.inset_faces"
    bl_label = "Inset Faces"
    bl_options = {'REGISTER', 'UNDO'}

    inset_thickness: bpy.props.FloatProperty(name="Thickness", default=0.2, subtype='DISTANCE')
    inset_depth: bpy.props.FloatProperty(name="Depth", default=0.0, subtype='DISTANCE')

    def execute(self, context):
        if context.active_object and context.active_object.type == 'MESH':
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.inset(thickness=self.inset_thickness, depth=self.inset_depth)
            bpy.ops.object.mode_set(mode='OBJECT')
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
        name="Width",
        description="Distance between the inner and outer edge",
        default=0.1,
        min=0.001,
        subtype='DISTANCE'
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'

    def execute(self, context):
        target_obj = context.active_object

        # Duplicate the object to create the cutter
        bpy.ops.object.duplicate()
        cutter_obj = context.active_object

        # Shrink the cutter object to create the inner void
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.transform.shrink_fatten(value=-self.width)
        bpy.ops.object.mode_set(mode='OBJECT')

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

        return {'FINISHED'}

classes = (
    MESH_OT_create_hole,
    MESH_OT_create_gear,
    MESH_OT_simple_extrude,
    MESH_OT_offset_edges,
    MESH_OT_inset_faces,
    MESH_OT_bevel_edges,
    MESH_OT_inner_radius,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
