bl_info = {
    "name": "Chunk Slicer",
    "description": "Slices an object into uniform chunks on selected axes.",
    "author": "Jake Mobley",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "Operator Search > Chunk Slicer",
    "category": "Modeling",
}

import bpy
import bmesh
import re
from mathutils import Vector
from collections import defaultdict
from my_pie_menus.resources import utils


class OBJECT_OT_chunk_slicer(bpy.types.Operator):
    """Slice object into chunks"""

    bl_idname = "object.chunk_slicer"
    bl_label = "Chunk Slicer"

    bl_options = {'REGISTER', "UNDO"}

    slice_type: bpy.props.EnumProperty(
        name="Slice Type",
        default="RELATIVE",
        description="Choose between setting slice size relative to object dimensions or to a fixed unit.",
        items=[
            ("RELATIVE", "Relative", "Slice relative on object dimensions."),
            ("FIXED", "Fixed", "Slice based on a fixed world space size."),
        ],
    )

    cell_size: bpy.props.FloatProperty(
        name="Cell Size",
        description="Cell size in world units. Sizes larger than the objects size on one axis will result in no effect.",
        default=0.3,
    )
    slice_qty: bpy.props.IntProperty(
        name="Number of Slices",
        description="Number of even slices to divide the object into",
        default=5,
        min=2,
    )
    cleanup_threshold: bpy.props.FloatProperty(
        name="Cleanup Threshold",
        description="Size of objects dimensions to delete after slice operation.",
        default=0.005,
        precision=4,
    )
    reset_origins: bpy.props.BoolProperty(
        name="Reset Origins",
        description="Set new chunk object origins to geometry center",
        default=True,
    )
    x: bpy.props.BoolProperty(
        name="X Axis",
        description="Slice on the X axis",
        default=True,
    )
    y: bpy.props.BoolProperty(
        name="Y Axis",
        description="Slice on the Y axis",
        default=True,
    )
    z: bpy.props.BoolProperty(
        name="Z Axis",
        description="Slice on the Z axis",
        default=True,
    )
    fill: bpy.props.BoolProperty(
        name="Fill",
        description="Use the 'Fill' option in the mesh bisect. Creates solid chunks, rather than a hollow mesh.",
        default=True,
    )

    force: bpy.props.BoolProperty(
        name="Force Non-Manifold",
        description="""Will slice the object, even if it has non-manifold geometry.
        Might cause issues with the operator being able to create 'solid' chunks, or create overlapping geometry.""",
        default=False,
    )

    axes = list('xyz')

    @property
    def num_axes_selected(self):
        '''To check if user has selected at least one axis before running'''
        return sum([self.x, self.y, self.z])

    def _get_plane_co(self, axis):
        '''Return the formatted coordinate for slicing on the current axis'''
        co = [0, 0, 0]
        index = self.axes.index(axis)
        co[index] = self.current_loc
        return co

    def _get_plane_no(self, axis):
        '''Return the formatted coordinate for the normal of the slice plane on the current axis'''
        plane_nos = {
            'x': Vector((1, 0, 0)),
            'y': Vector((0, 1, 0)),
            'z': Vector((0, 0, 1)),
        }
        return Vector(plane_nos[axis])

    def _slices_in_axis(self, axis):
        return int(getattr(self.num_slices, axis))

    def _bmesh(cls, context):
        obj = context.obj
        mesh = obj.data
        self.bm = bmesh.new()
        self.bm.from_mesh(mesh)

    def _get_start_loc(self, axis):
        '''Get the initial slice coordinate in an axis.'''
        loc = min([getattr(v.co, axis) for v in self.mesh.vertices])
        return loc

    def _get_end_loc(self, axis):
        '''Get the final bounds in an axis.'''
        return max([getattr(v.co, axis) for v in self.mesh.vertices])

    def _loc_overlaps(self, loc, axis):
        end_loc = self._get_end_loc(axis)
        loc_diff = loc - end_loc
        overlaps = abs(loc_diff) <= 0.001
        if overlaps:
            msg = "is not valid"
        else:
            msg = "is valid"
        print(f"New Loc: {loc}, End Loc: {end_loc}, Difference:{loc_diff}, Location {msg}.")
        return overlaps

    @property
    def _get_slice_index(self):
        axis, index = self.current_axis, self.current_index
        return self.slice_locs[axis][index]

    def _mesh_has_manifold_geom(self):
        return all([e.is_manifold for e in self.bm.edges[:]])

    def _rename_temp(self, object):
        object.name = f"__Sliced__{self.current_index}"

    def _duplicate_obj(self, context):
        '''Duplicate the current object, set it to be the current slice_object
        and return it.'''

        new_obj = self.obj.copy()
        new_obj.data = self.obj.data.copy()
        self._rename_temp(new_obj)
        context.collection.objects.link(new_obj)
        bpy.ops.object.select_all(action="DESELECT")
        context.view_layer.objects.active = new_obj
        self.current_obj = new_obj

    def _slice(self, axis, clear_inner=False, clear_outer=False):
        '''Perform the steps required to slice the current object.'''
        self.current_obj.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.bisect(
            plane_co=self._get_plane_co(axis),
            plane_no=self._get_plane_no(axis),
            clear_inner=clear_inner,
            clear_outer=clear_outer,
            use_fill=self.fill,
        )
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")

    def _slice_operation(self, context):
        '''Perform larger scale steps to handle slicing of objects
        and organization of each object being sliced in succession'''

        # Works by creating a duplicate of the object and, depending on where
        # the current cut is taking place, will cut and either remove before the
        # chunk to keep or after, or both
        #
        #              slice1      slice2
        #         ________ : _______ : _______
        #        |        |:|       |:|       |
        #        | before |:| chunk |:| after |
        #        |        |:|  to   |:|       |
        #        |        |:| keep  |:|       |
        #
        #

        self._duplicate_obj(context)
        axis = self.current_axis
        i = self.current_index
        # first cut (index == 0) we only need to slice one time, otherwise we slice directly
        # one the far edge of the object.
        if i != 0:
            old_loc = self.current_loc
            self.current_loc = self.slice_locs[axis][i - 1]
            self._slice(axis, clear_inner=True)
            self.current_loc = old_loc
        # every cut in between we cut the before and the after.
        # last cut we also only cut once, on the before.
        if i != self._slices_in_axis(axis) and not self._loc_overlaps(self.current_loc, axis):
            self._slice(axis, clear_outer=True)

    def _invalid_dimensions(self, dims):
        '''Check if the new sliced object is too small to be valid'''
        return sum([v <= self.cleanup_threshold for v in dims]) > 1

    def _cleanup_objs(self, context):
        '''Check sliced objects for existing geometry/valid dimensions and then rename,
        otherwise delete.'''

        context.scene.objects.update()
        objs = context.view_layer.objects
        bpy.ops.object.select_all(action="DESELECT")
        cleanup_objs = [obj for obj in objs if "__Sliced__" in obj.name]
        orig_name = re.sub("(\.\d+$)", '', self.orig_name)

        for obj in cleanup_objs:
            dims = obj.dimensions
            if not obj.data.vertices[:] or self._invalid_dimensions(dims):
                context.collection.objects.unlink(obj)
                cleanup_objs.remove(obj)
        for i, obj in enumerate(cleanup_objs):
            if self.reset_origins:
                obj.select_set(True)
            new_name = f"{orig_name}_Sliced_{i+1}"
            obj.name = new_name
        if self.reset_origins:
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
        bpy.ops.object.select_all(action="DESELECT")

    def _get_slice_locs(self):
        self.slice_locs = defaultdict(list)

        if self.slice_type == "FIXED":
            self.num_slices = Vector([dim // self.cell_size for dim in self.dims])
            for axis in self.axes:
                current_loc = self._get_start_loc(axis)
                for i in range(self._slices_in_axis(axis) + 1):
                    new_loc = current_loc + self.cell_size
                    self.slice_locs[axis].append(new_loc)
                    current_loc = new_loc

        elif self.slice_type == "RELATIVE":
            qty = self.slice_qty + 1
            self.cell_sizes = Vector([dim / qty for dim in self.dims])
            self.num_slices = Vector([qty] * 3)
            for axis in self.axes:
                current_loc = self._get_start_loc(axis)
                for i in range(self._slices_in_axis(axis)):
                    new_loc = current_loc + getattr(self.cell_sizes, axis)
                    self.slice_locs[axis].append(new_loc)
                    current_loc = new_loc

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and context.mode == "OBJECT"

    def invoke(self, context, event):
        self.obj = context.active_object
        self.orig_name = self.obj.name
        self.mesh = self.obj.data
        self.bm = bmesh.new()
        self.bm.from_mesh(self.mesh)

        # check for manifold geo before running operator.

        self.dims = self.obj.dimensions
        self.current_obj = self.obj
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        self._get_slice_locs()
        if not self.force and not (self._mesh_has_manifold_geom()):
            self.report(
                {"WARNING"}, "Mesh must have manifold geometry to perform slice operation. Operation Cancelled."
            )
            return {"CANCELLED"}
        sliced_x = []
        sliced_y = []

        # Starts with the currently selected object,
        # duplicates that, slices that in one axis,
        # appends the new sliced object to the sliced list
        # then each successive slice axis will pull from those
        # sliced objects to repeat the process. Depending on which axes the user has selected,
        # the slice_axis might have to shift objects around to get the slice the correct Objects

        if self.num_axes_selected == 0:
            self.report({"ERROR"}, "Must select at least one slice axis.")
            return {"CANCELLED"}
        if self.x:
            self.current_axis = "x"
            x_locs = self.slice_locs[self.current_axis]
            for index, loc in enumerate(x_locs):
                self.current_loc = loc
                self.current_index = index
                self._slice_operation(context)
                sliced_x.append(self.current_obj)
            self.obj.hide_set(True)
            self.obj.name = "Sliced_Original"
        if self.y:
            self.current_axis = "y"
            y_locs = self.slice_locs[self.current_axis]
            # like here, if user didn't choose to slice on the x-axis, we just pretend
            # the sliced_x list was just the first object all along.
            if not sliced_x:
                sliced_x = [self.obj]
            for obj in sliced_x:
                self.obj = obj
                for index, loc in enumerate(y_locs):
                    self.current_loc = loc
                    self.current_index = index
                    self._slice_operation(context)
                    sliced_y.append(self.current_obj)
                context.collection.objects.unlink(obj)
                # context.collection.objects.unlink(obj)
        if self.z:
            self.current_axis = "z"
            z_locs = self.slice_locs[self.current_axis]
            # same deal, if user only chose z then the slice_y is just the first obj.
            # else if they chose x and z, then pretend that sliced_y is sliced_x
            # without actually slicing y.
            if not sliced_y:
                if not sliced_x:
                    sliced_y = [self.obj]
                else:
                    sliced_y = sliced_x
            for obj in sliced_y:
                self.obj = obj
                for index, loc in enumerate(z_locs):
                    self.current_loc = loc
                    self.current_index = index
                    self._slice_operation(context)
                context.collection.objects.unlink(obj)
        self._cleanup_objs(context)
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        row = col.row()
        row.ui_units_y += 1.3
        row.prop(self, "slice_type")
        if self.slice_type == "FIXED":
            col.prop(self, "cell_size")
        elif self.slice_type == "RELATIVE":
            col.prop(self, "slice_qty")
        col = layout.column(align=True)
        col.prop(self, "cleanup_threshold")
        col.prop(self, "reset_origins")
        row = layout.row()
        row.prop(self, "x")
        row.prop(self, "y")
        row.prop(self, "z")
        col = layout.column(align=True)
        col.prop(self, "fill")
        col.prop(self, "force")


classes = (OBJECT_OT_chunk_slicer,)


addon_keymaps = []


def register():
    bpy.utils.register_class(OBJECT_OT_chunk_slicer)

    # set keymap
    keymap_operator = "object.chunk_slicer"
    name = "3D View"
    letter = "SLASH"
    shift = 1
    ctrl = 0
    alt = 1
    space_type = "VIEW_3D"

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    km = kc.keymaps.new(name=name, space_type=space_type)
    kmi = km.keymap_items.new(keymap_operator, letter, 'PRESS', shift=shift, ctrl=ctrl, alt=alt)
    kmi.active = True
    addon_keymaps.append((km, kmi))


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_chunk_slicer)
    utils.unregister_keymaps(addon_keymaps)


if __name__ == "__main__":
    register()
