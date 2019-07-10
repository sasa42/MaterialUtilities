# Ported from 2.6 (& 2.7) to 2.8 by
#    Christopher Hindefjord (chrishinde) 2019
#
# ## Port based on 2010 version by MichaelW with some code added from latest 2.7x version
# ## Same code may be attributed to one of the follwing awesome people!
#  (c) 2016 meta-androcto, parts based on work by Saidenka, lijenstina
#  Materials Utils: by MichaleW, lijenstina,
#       (some code thanks to: CoDEmanX, SynaGl0w, ideasman42)
#  Link to base names: Sybren, Texture renamer: Yadoob
# ###
#
#
# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Material Utilities",
    "author": "chrishinde",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Shift + Q key",
    "description": "Menu of material tools (assign, select..) in the 3D View",
    "warning": "Under development!",
    "wiki_url": "https://github.com/ChrisHinde/MaterialUtils",
    "category": "Materials"
}

"""
This script has several functions and operators, grouped for convenience:

* assign material:
    offers the user a list of ALL the materials in the blend file and an
    additional "new" entry the chosen material will be assigned to all the
    selected objects in object mode.

    in edit mode the selected polygons get the selected material applied.

    if the user chose "new" the new material can be renamed using the
    "last operator" section of the toolbox.


* select by material
    in object mode this offers the user a menu of all materials in the blend
    file any objects using the selected material will become selected, any
    objects without the material will be removed from selection.

    in edit mode:  the menu offers only the materials attached to the current
    object. It will select the polygons that use the material and deselect those
    that do not.

* clean material slots
    for all selected objects any empty material slots or material slots with
    materials that are not used by the mesh polygons or splines will be removed.

* remove material slots
    removes all material slots of the active (or selected) object(s).

* replace materials
    lets your replace one material by another. Optionally for all objects in
    the blend, otherwise for selected editable objects only. An additional
    option allows you to update object selection, to indicate which objects
    were affected and which not.

* set fake user
    enable/disable fake user for materials. You can chose for which materials
    it shall be set, materials of active / selected / objects in current scene
    or used / unused / all materials.

"""


import bpy
import bmesh
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, EnumProperty
#from bpy.types import EnumPropertyItem

#from .functions import *

# -----------------------------------------------------------------------------
# functions  (To be moved to separate file)


def mu_assign_material_slots(object, material_list):
    """Given an object and a list of material names removes all material slots from the object
       adds new ones for each material in the material list, adds the materials to the slots as well."""

    scene = bpy.context.scene
    active_object = bpy.context.active_object
    bpy.context.view_layer.objects.active = object

    for s in object.material_slots:
        bpy.ops.object.material_slot_remove()

    # re-add them and assign material
    i = 0
    for mat in material_list:
        material = bpy.data.materials[mat]
        object.data.materials.append(material)
        i += 1

    # restore active object:
    bpy.context.view_layer.objects.active = active_object

def mu_assign_to_data(object, material, index, edit_mode, all = True):
    """Assign the material to the object data (polygons/splines)"""

    if object.type == 'MESH':
        # now assign the material to the mesh
        mesh = object.data
        if all:
            for poly in mesh.polygons:
                poly.material_index = index
        else:
            for poly in mesh.polygons:
                if poly.select:
                    poly.material_index = index

        mesh.update()

    elif object.type in {'CURVE', 'SURFACE', 'TEXT'}:
        bpy.ops.object.mode_set(mode = 'EDIT')    # This only works in Edit mode

        # If operator was run in Object mode
        if not edit_mode:
            # Select everything in Edit mode
            bpy.ops.curve.select_all(action = 'SELECT')

        bpy.ops.object.material_slot_assign()   # Assign material of the current slot to selection

        if not edit_mode:
            bpy.ops.object.mode_set(mode = 'OBJECT')


def mu_assign_material(self, material_name = "Default", override_type = 'APPEND_MATERIAL'):
    """Assign the defined material to selected polygons/objects"""

    print("ASSMat: " + material_name + " : " + override_type)

    # get active object so we can restore it later
    active_object = bpy.context.active_object

    edit_mode = False
    all_polygons = True
    if active_object.mode == 'EDIT':
        edit_mode = True
        all_polygons = False
        bpy.ops.object.mode_set()

    # check if material exists, if it doesn't then create it
    found = False
    for material in bpy.data.materials:
        if material.name == material_name:
            target = material
            found = True
            break

    if not found:
        target = bpy.data.materials.new(material_name)
        target.use_nodes = True         # When do we not want nodes today?


    index = 0
    objects = bpy.context.selected_editable_objects

    for obj in objects:
        # set the active object to our object
        scene = bpy.context.scene
        bpy.context.view_layer.objects.active = obj

        # If we should override all current material slots
        if override_type == 'OVERRIDE_ALL' or obj.type == 'META':
            # Clear out the material slots
            obj.data.materials.clear()
            # and then append the target material
            obj.data.materials.append(target)

            # Assign the material to the data/palys, to avoid weird problems
            mu_assign_to_data(obj, target, 0, edit_mode, True)

            if obj.type == 'META':
                self.report({'INFO'}, "Meta balls only support one material, all other materials overriden!")

        # If we should override each material slot
        elif override_type == 'OVERRIDE_SLOTS':
            i = 0
            # go through each slot
            for material in obj.material_slots:
                # assign the target material to current slot
                obj.data.materials[i] = target
                i += 1

        # if we should keep the material slots and just append the selected material (if not already assigned)
        elif override_type == 'APPEND_MATERIAL':
            found = False
            i = 0
            material_slots = obj.material_slots

            # check material slots for material_name materia
            for material in material_slots:
                if material.name == material_name:
                    found = True
                    index = i
                    # make slot active
                    obj.active_material_index = i
                    break
                i += 1

            if not found:
                # the material is not attached to the object
                if (len(obj.data.materials) == 1) and not edit_mode:
                    # in object mode, override the material if it's just one slot used
                    obj.data.materials[0] = target
                    index = 0
                else:
                    # In Edit mode, or if there's not a slot, append the assigned material
                    #  If we're overriding, there's currently no materials at all, so after this there will be 1
                    #  If not, this adds another slot with the assigned material
                    index = len(obj.data.materials)
                    obj.data.materials.append(target)
                    obj.active_material_index = index

                mu_assign_to_data(obj, target, index, edit_mode, all_polygons)

    #restore the active object
    bpy.context.view_layer.objects.active = active_object

    if edit_mode:
        bpy.ops.object.mode_set(mode='EDIT')

    print("End of Assign material!")
    return {'FINISHED'}


def mu_select_by_material_name(self, find_material_name, extend_selection = False):
    """Searches through all objects, or the polygons/curves of the current object
    to find and select objects/data with the desired material"""

    # in object mode selects all objects with material find_material_name
    # in edit mode selects all polygons with material find_material_name

    find_material = bpy.data.materials.get(find_material_name)

    if find_material is None:
        self.report({'INFO'}, "The material " + find_material_name + " doesn't exists!")
        return {'CANCELLED'}

    # check for edit_mode
    edit_mode = False
    found_material = False

    scene = bpy.context.scene

    # set selection mode to polygons
    scene.tool_settings.mesh_select_mode = False, False, True

    active_object = bpy.context.active_object

    if active_object.mode == 'EDIT':
        edit_mode = True

    if not edit_mode:
        objects = bpy.data.objects
        for obj in objects:
            if obj.type in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}:
                mat_slots = obj.material_slots
                for material in mat_slots:
                    if material.material == find_material:
                        obj.select_set(state = True)

                        found_material = True

                        # the active object may not have the material!
                        # set it to one that does!
                        bpy.context.view_layer.objects.active = obj
                        break
                    else:
                        if not extend_selection:
                            obj.select_set(state=False)

            #deselect non-meshes
            elif not extend_selection:
                obj.select_set(state=False)

        if not found_material:
            self.report({'INFO'}, "No objects found with the material " + find_material_name + "!")
            return {'CANCELLED'}

    else:
        # it's edit_mode, so select the polygons

        obj = active_object

        if obj.type == 'MESH':
            # if not extending the selection, deselect all first
            #  (Without this, edges/faces were still selected
            #   while the faces were deselcted)
            if not extend_selection:
                bpy.ops.mesh.select_all(action = 'DESELECT')

            bpy.ops.object.mode_set()

            mat_slots = obj.material_slots

            # same material can be on multiple slots
            slot_indeces = []
            i = 0
            for material in mat_slots:
                if material.material == find_material:
                    slot_indeces.append(i)
                i += 1

            mesh = obj.data

            for poly in mesh.polygons:
                if poly.material_index in slot_indeces:
                    poly.select = True
                    found_material = True
                elif not extend_selection:
                    poly.select = False

            mesh.update()

            bpy.ops.object.mode_set(mode = 'EDIT')

            if not found_material:
                self.report({'INFO'}, "Material " + find_material_name + " isn't assigned to any faces!")
                return {'CANCELLED'}

        elif obj.type in {'CURVE', 'SURFACE'}:
            # For Curve objects, there can only be one material per spline
            #  and thus each spline is linked to one material slot.
            #  So to not have to care for different data structures for different curve types,
            #  we use the material slots and the built in selection methods
            #  (Technically, this should work for meshes as well)

            mat_slots = obj.material_slots

            i = 0
            for material in mat_slots:
                bpy.context.active_object.active_material_index = i

                if material.material == find_material:
                    bpy.ops.object.material_slot_select()
                    found_material = True
                elif not extend_selection:
                    bpy.ops.object.material_slot_deselect()

                i += 1

            if not found_material:
                self.report({'INFO'}, "Material " + find_material_name + " isn't assigned to slots!")

        else:
            # Some object types are not supported
            #  mostly because don't really support selecting by material (like Font/Text objects)
            #  ore that they don't support multiple materials/are just "weird" (i.e. Meta balls)
            self.report({'WARNING'}, "The type '" + obj.type + "' isn't supported in Edit mode by Material Utilities!")
            return {'CANCELLED'}

    return {'FINISHED'}


def mu_copy_material_to_others(self):
    """Copy the material to of the current object to the other seleceted all_objects"""
    # Currently uses the built-in method
    #  This could be extended to work in edit mode as well

    #active_object = context.active_object

    bpy.ops.object.material_slot_copy()

    return {'FINISHED'}


def mu_cleanmatslots(self):
    """Clean the material slots of the seleceted objects"""

    # check for edit mode
    edit_mode = False
    active_object = bpy.context.active_object
    if active_object.mode == 'EDIT':
        edit_mode = True
        bpy.ops.object.mode_set()

    objects = bpy.context.selected_editable_objects

    for obj in objects:
        used_mat_index = []  # we'll store used materials indices here
        assigned_materials = []
        material_list = []
        material_names = []

        materials = obj.material_slots.keys()

        if obj.type == 'MESH':
            # check the polygons on the mesh to build a list of used materials
            mesh = obj.data

            for poly in mesh.polygons:
                # get the material index for this face...
                material_index = poly.material_index

                if material_index >= len(materials):
                    poly.select = True
                    self.report({'ERROR'},
                                "A poly with an invalid material was found, this should not happen! Canceling!")
                    return {'CANCELLED'}

                # indices will be lost: Store face mat use by name
                current_mat = materials[material_index]
                assigned_materials.append(current_mat)

                # check if index is already listed as used or not
                found = False
                for mat in used_mat_index:
                    if mat == material_index:
                        found = True

                if not found:
                    # add this index to the list
                    used_mat_index.append(material_index)

            # re-assign the used materials to the mesh and leave out the unused
            for u in used_mat_index:
                material_list.append(materials[u])
                # we'll need a list of names to get the face indices...
                material_names.append(materials[u])

            mu_assign_material_slots(obj, material_list)

            # restore face indices:
            i = 0
            for poly in mesh.polygons:
                material_index = material_names.index(assigned_materials[i])
                poly.material_index = material_index
                i += 1

        elif obj.type in {'CURVE', 'SURFACE'}:

            splines = obj.data.splines

            for spline in splines:
                # Get the material index of this spline
                material_index = spline.material_index

                # indices will be last: Store material use by name
                current_mat = materials[material_index]
                assigned_materials.append(current_mat)

                # check if indek is already listed as used or not
                found = False
                for mat in used_mat_index:
                    if mat == material_index:
                        found = True

                if not found:
                    # add this index to the list
                    used_mat_index.append(material_index)

            # re-assigned the used materials to the curve and leave out the unused
            for u in used_mat_index:
                material_list.append(materials[u])
                # we'll need a list of names to get the face indices
                material_names.append(materials[u])

            mu_assign_material_slots(obj, material_list)

            # restore spline indices
            i = 0
            for spline in splines:
                material_index = material_names.index(assigned_materials[i])
                spline.material_index = material_index
                i += 1

        else:
            # Some object types are not supported
            self.report({'WARNING'},
                        "The type '" + obj.type + "' isn't currently supported " +
                        "for Material slots cleaning by Material Utilities!")

    if edit_mode:
        bpy.ops.object.mode_set(mode='EDIT')


def mu_remove_material(self, for_active_object = False):
    """Remove the active material slot from selected object(s)"""

    if for_active_object:
        bpy.ops.object.material_slot_remove()
    else:
        last_active = bpy.context.active_object
        objects = bpy.context.selected_editable_objects

        for obj in objects:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.material_slot_remove()

        bpy.context.view_layer.objects.active =  last_active

    return {'FINISHED'}

def mu_remove_all_materials(self, for_active_object = False):
    """Remove all material slots from selected object(s)"""

    if for_active_object:
        obj = bpy.context.active_object

        # Clear out the material slots
        obj.data.materials.clear()

    else:
        last_active = bpy.context.active_object
        objects = bpy.context.selected_editable_objects

        for obj in objects:
            obj.data.materials.clear()

        bpy.context.view_layer.objects.active = last_active

    return {'FINISHED'}


def mu_replace_material(material_a, material_b, all_objects=False, update_selection=False):
    """Replace one material with another material"""

    # material_a is the name of original material
    # material_b is the name of the material to replace it with
    # 'all' will replace throughout the blend file

    mat_org = bpy.data.materials.get(material_a)
    mat_rep = bpy.data.materials.get(material_b)

    if mat_org != mat_rep and None not in (mat_org, mat_rep):
        # Store active object
        scn = bpy.context.scene

        if all_objects:
            objs = bpy.data.objects
        else:
            objs = bpy.context.selected_editable_objects

        for obj in objs:
            if obj.type == 'MESH':
                match = False

                for mat in obj.material_slots:
                    if mat.material == mat_org:
                        mat.material = mat_rep

                        # Indicate which objects were affected
                        if update_selection:
                            obj.select_set(state = True)
                            match = True

                if update_selection and not match:
                    obj.select_set(state = False)

    return {'FINISHED'}


def mu_set_fake_user(self, fake_user, materials):
    """Set the fake user flag for the objects material"""

    if materials == 'ALL':
        mats = (mat for mat in bpy.data.materials if mat.library is None)
    elif materials == 'UNUSED':
        mats = (mat for mat in bpy.data.materials if mat.library is None and mat.users == 0)
    else:
        mats = []
        if materials == 'ACTIVE':
            objs = [bpy.context.active_object]
        elif materials == 'SELECTED':
            objs = bpy.context.selected_objects
        elif materials == 'SCENE':
            objs = bpy.context.scene.objects
        else: # materials == 'USED'
            objs = bpy.data.objects
            # Maybe check for users > 0 instead?

        mats = (mat for ob in objs if hasattr(ob.data, "materials") for mat in ob.data.materials if mat.library is None)

    if fake_user == 'TOGGLE':
        done_mats = []
        for mat in mats:
            if  not mat.name in done_mats:
                mat.use_fake_user = not mat.use_fake_user
            done_mats.append(mat.name)
    else:
        fake_user_val = fake_user == 'ON'
        for mat in mats:
            mat.use_fake_user = fake_user_val

    for area in bpy.context.screen.areas:
        if area.type in ('PROPERTIES', 'NODE_EDITOR'):
            area.tag_redraw()

    return {'FINISHED'}


def mu_change_material_link(self, link, affect, override_data_material = False):
    """Change what the materials are linked to (Object or Data), while keeping materials assigned"""

    objects = []

    if affect == "ACTIVE":
        objects = [bpy.context.active_object]
    elif affect == "SELECTED":
        objects = bpy.context.selected_objects
    elif affect == "SCENE":
        objects = bpy.context.scene.objects
    elif affect == "ALL":
        objects = bpy.data.objects

    for object in objects:
        for slot in object.material_slots:
            present_material = slot.material

            if link == 'TOGGLE':
                slot.link = ('DATA' if slot.link == 'OBJECT' else 'OBJECT')
            else:
                slot.link = link

            if slot.link == 'OBJECT' or override_data_material:
                slot.material = present_material

    return {'FINISHED'}


# -----------------------------------------------------------------------------
# operator classes (To be moved to separate file)

class VIEW3D_OT_materialutilities_assign_material_edit(bpy.types.Operator):
    """Assign a material to the current selection"""

    bl_idname = "view3d.materialutilities_assign_material_edit"
    bl_label = "Assign Material (Material Utilities)"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: StringProperty(
            name = 'Material Name',
            description = 'Name of Material to assign to current selection',
            default = "",
            maxlen = 63
            )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        material_name = self.material_name
        return mu_assign_material(self, material_name, 'APPEND_MATERIAL')

override_types = [
    ('OVERRIDE_ALL', "Override all assigned slots",
        "Remove any current material slots, and assign the current material"),
    ('OVERRIDE_SLOTS', 'Assign material to each slot',
        'Keep the material slots, but assign the selected material in each slot'),
    ('APPEND_MATERIAL', 'Append Material',
        'Add the material in a new slot, and assign it to the whole object')
]

class VIEW3D_OT_materialutilities_assign_material_object(bpy.types.Operator):
    """Assign a material to the current selection
    (See the operator panel [F9] for more options)"""

    bl_idname = "view3d.materialutilities_assign_material_object"
    bl_label = "Assign Material (Material Utilities)"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: StringProperty(
            name = 'Material Name',
            description = 'Name of Material to assign to current selection',
            default = "",
            maxlen = 63
            )
    override_type: EnumProperty(
            name = 'Assignment method',
            description = '',
            items = override_types
            )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        material_name = self.material_name
        override_type = self.override_type
        result = mu_assign_material(self, material_name, override_type)
        print("Material Assigned!")
        return result


class VIEW3D_OT_materialutilities_select_by_material_name(bpy.types.Operator):
    """Select geometry that has the chosen material assigned to it
    (See the operator panel [F9] for more options)"""

    bl_idname = "view3d.materialutilities_select_by_material_name"
    bl_label = "Select By Material Name (Material Utilities)"
    bl_options = {'REGISTER', 'UNDO'}

    extend: BoolProperty(
            name = 'Extend Selection',
            description = 'Keeps the current selection and adds faces with the material to the selection'
            )
    material_name: StringProperty(
            name = 'Material Name',
            description = 'Name of Material to Select',
            maxlen = 63,
            )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        material_name = self.material_name
        ext = self.extend
        return mu_select_by_material_name(self, material_name, ext)


class VIEW3D_OT_materialutilities_copy_material_to_others(bpy.types.Operator):
    """Copy the material(s) of the active object to the other selected objects"""

    bl_idname = "view3d.materialutilities_copy_material_to_others"
    bl_label = "Copy material(s) to others (Material Utilities)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None) and (context.active_object.mode != 'EDIT')

    def execute(self, context):
        return mu_copy_material_to_others(self)


class VIEW3D_OT_materialutilities_clean_material_slots(bpy.types.Operator):
    """Removes any material slots from the selected objects that are not used"""

    bl_idname = "view3d.materialutilities_clean_material_slots"
    bl_label = "Clean Material Slots (Material Utilities)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        mu_cleanmatslots(self)
        return {'FINISHED'}


class VIEW3D_OT_materialutilities_remove_material_slot(bpy.types.Operator):
    """Remove the active material slot from selected object(s)
    (See the operator panel [F9] for more options)"""

    bl_idname = "view3d.materialutilities_remove_material_slot"
    bl_label = "Remove Active Material Slot (Material Utilities)"
    bl_options = {'REGISTER', 'UNDO'}

    only_active: BoolProperty(
            name = 'Only active object',
            description = 'Only remove the active material slot for the active object ' +
                            '(otherwise do it for every selected object)'
            )

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None) and (context.active_object.mode != 'EDIT')

    def execute(self, context):
        return mu_remove_material(self, self.only_active)

class VIEW3D_OT_materialutilities_remove_all_material_slots(bpy.types.Operator):
    """Remove all material slots from selected object(s)
    (See the operator panel [F9] for more options)"""

    bl_idname = "view3d.materialutilities_remove_all_material_slots"
    bl_label = "Remove All Material Slots (Material Utilities)"
    bl_options = {'REGISTER', 'UNDO'}

    only_active: BoolProperty(
            name = 'Only active object',
            description = 'Only remove the material slots for the active object ' +
                            '(otherwise do it for every selected object)'
            )

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None) and (context.active_object.mode != 'EDIT')

    def execute(self, context):
        return mu_remove_all_materials(self, self.only_active)


class VIEW3D_OT_materialutilities_replace_material(bpy.types.Operator):
    """Replace a material by name"""
    bl_idname = "view3d.materialutilities_replace_material"
    bl_label = "Replace Material (Material Utilities)"
    bl_options = {'REGISTER', 'UNDO'}

    matorg: StringProperty(
            name = "Original",
            description = "Material to replace",
            maxlen = 63,
            )
    matrep: StringProperty(name="Replacement",
            description = "Replacement material",
            maxlen = 63,
            )
    all_objects: BoolProperty(
            name = "All objects",
            description = "Replace for all objects in this blend file",
            default = True,
            )
    update_selection: BoolProperty(
            name = "Update Selection",
            description = "Select affected objects and deselect unaffected",
            default = True,
            )

    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, "matorg", bpy.data, "materials")
        layout.prop_search(self, "matrep", bpy.data, "materials")
        layout.prop(self, "all_objects")
        layout.prop(self, "update_selection")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return mu_replace_material(self.matorg, self.matrep, self.all_objects, self.update_selection)


class VIEW3D_OT_materialutilities_fake_user_set(bpy.types.Operator):
    """Enable/disable fake user for materials"""

    bl_idname = "view3d.materialutilities_fake_user_set"
    bl_label = "Set Fake User (Material Utilities)"
    bl_options = {'REGISTER', 'UNDO'}

    fake_user: EnumProperty(
            name = "Fake User",
            description = "Turn fake user on or off",
            items = (('ON', "On", "Enable fake user"),
                     ('OFF', "Off", "Disable fake user"),
                     ('TOGGLE', "Toggle", "Toggle fake user")),
            default = 'TOGGLE'
            )

    materials: EnumProperty(
            name = "Materials",
            description = "Which materials of objects to affect",
            items = (('ACTIVE', "Active object", "Materials of active object only"),
                     ('SELECTED', "Selected objects", "Materials of selected objects"),
                     ('SCENE', "Scene objects", "Materials of objects in current scene"),
                     ('USED', "Used", "All materials used by objects"),
                     ('UNUSED', "Unused", "Currently unused materials"),
                     ('ALL', "All", "All materials in this blend file")),
            default = 'UNUSED'
            )

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "fake_user", expand = True)
        layout.prop(self, "materials")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return mu_set_fake_user(self, self.fake_user, self.materials)


class VIEW3D_OT_materialutilities_change_material_link(bpy.types.Operator):
    """Link the materials to Data or Object, while keepng materials assigned"""

    bl_idname = "view3d.materialutilities_change_material_link"
    bl_label = "Change Material Linking (Material Utilities)"
    bl_options = {'REGISTER', 'UNDO'}


    override: BoolProperty(
            name = "Override Data material",
            description = "Override the materials assigned to the object data/mesh when switching to 'Linked to Data'\n" +
                            "(WARNING: This will override the materials of other linked objects, " +
                             "which have the materials linked to Data)",
            default = False,
            )
    link_to: EnumProperty(
            name = "Link",
            description = "What should the material be linked to",
            items = (('DATA', "Data", "Link the materials to the data"),
                     ('OBJECT', "Object", "Link the materials to the object"),
                     ('TOGGLE', "Toggle", "Toggle what the materials are currently linked to")),
            default = 'OBJECT'
            )

    affect: EnumProperty(
            name = "Materials",
            description = "Which materials of objects to affect",
            items = (('ACTIVE', "Active object", "Materials of active object only"),
                     ('SELECTED', "Selected objects", "Materials of selected objects"),
                     ('SCENE', "Scene objects", "Materials of objects in current scene"),
                     ('ALL', "All", "All materials in this blend file")),
            default = 'SELECTED'
            )

    @classmethod
    def poll(cls, context):
        return (context.active_object is not None)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "override")
        layout.prop(self, "link_to")
        layout.prop(self, "affect")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return mu_change_material_link(self, self.link_to, self.affect, self.override)

class MATERIAL_OT_materialutilities_merge_base_names(bpy.types.Operator):
    """Merges materials that has the same base names but ends with .xxx (.001, .002 etc)"""

    bl_idname = "material.materialutilities_merge_base_names"
    bl_label = "Merge Base Names"
    bl_description = "Merge materials that has the same base names but ends with .xxx (.001, .002 etc)"

    material_base_name: StringProperty(
                            name = "Material Base Name",
                            default = "",
                            description = 'Base name for materials to merge ' +
                                          '(e.g. "Material" is the base name of "Material.001", "Material.002" etc.)'
                            )
    is_auto: BoolProperty(
                            name = "Auto Merge",
                            description = "Find all available duplicate materials and Merge them"
                            )

    is_not_undo = False
    material_error = []          # collect mat for warning messages


    def replace_name(self):
        """If the user chooses a material like 'Material.042', clean it up to get a base name ('Material')"""

        # use the chosen material as a base one, check if there is a name
        self.check_no_name = (False if self.material_base_name in {""} else True)

        # No need to do this if it's already "clean"
        #  (Also lessens the potential of error given about the material with the Base name)
        if '.' not in self.material_base_name:
            return

        if self.check_no_name is True:
            for mat in bpy.data.materials:
                name = mat.name

                if name == self.material_base_name:
                    try:
                        base, suffix = name.rsplit('.', 1)

                        # trigger the exception
                        num = int(suffix, 10)
                        self.material_base_name = base
                        mat.name = self.material_base_name
                        return
                    except ValueError:
                        if name not in self.material_error:
                            self.material_error.append(name)
                        return

        return

    def split_name(self, material):
        """Split the material name into a base and a suffix"""

        name = material.name

        # No need to do this if it's already "clean"/there is no suffix
        if '.' not in name:
            return name, None

        base, suffix = name.rsplit('.', 1)

        try:
            # trigger the exception
            num = int(suffix, 10)
        except ValueError:
            # Not a numeric suffix
            # Don't report on materials not actually included in the merge!
            if ((self.is_auto or base == self.material_base_name)
                 and (name not in self.material_error)):
                self.material_error.append(name)
            return name, None

        if self.is_auto is False:
            if base == self.material_base_name:
                return base, suffix
            else:
                return name, None

        return base, suffix

    def fixup_slot(self, slot):
        """Fix material slots that was assigned to materials now removed"""

        if not slot.material:
            return

        base, suffix = self.split_name(slot.material)
        if suffix is None:
            return

        try:
            base_mat = bpy.data.materials[base]
        except KeyError:
            print("\n[Materials Utilities Specials]\nLink to base names\nError:"
                  "Base material %r not found\n" % base)
            return

        slot.material = base_mat

    def main_loop(self, context):
        """Loops through all objects and material slots to make sure they are assigned to the right material"""

        for obj in context.scene.objects:
            for slot in obj.material_slots:
                self.fixup_slot(slot)

    @classmethod
    def poll(self, context):
        return context.active_object is not None

    def draw(self, context):
        layout = self.layout

        box_1 = layout.box()
        box_1.prop_search(self, "material_base_name", bpy.data, "materials")
        box_1.enabled = not self.is_auto
        layout.separator()

        box_2 = layout.box()
        box_2.prop(self, "is_auto", text = "Auto Rename/Replace", icon = "SYNTAX_ON")

    def invoke(self, context, event):
        self.is_not_undo = True
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        # Reset Material errors, otherwise we risk reporting errors erroneously..
        self.material_error = []

        if not self.is_auto:
            self.replace_name()

            if self.check_no_name:
                self.main_loop(context)
            else:
                self.report({'WARNING'}, "No Material Base Name given!")

                self.is_not_undo = False
                return {'CANCELLED'}

        self.main_loop(context)

        if self.material_error:
            materials = ", ".join(self.material_error)

            if len(self.material_error) == 1:
                waswere = " was"
                suff_s = ""
            else:
                waswere = " were"
                suff_s = "s"

            self.report({'WARNING'}, materials + waswere + " not removed or set as Base" + suff_s)

        self.is_not_undo = False
        return {'FINISHED'}

class MATERIAL_OT_materialutilities_material_slot_move(bpy.types.Operator):
    """Move the active material slot"""

    bl_idname = "material.materialutilities_slot_move"
    bl_label = "Move Slot"
    bl_description = "Move the material slot"
    bl_options = {'REGISTER', 'UNDO'}

    movement: EnumProperty(
                name = "Move",
                description = "How to move the material slot",
                items = (('TOP', "Top", "Move slot to the top"),
                         ('BOTTOM', "Bottom", "Move slot bottom"))
                )

    @classmethod
    def poll(self, context):
        # would prefer to access sely.movement here, but can'-'t..
        obj = context.active_object
        if not obj:
            return False
        if (obj.active_material_index < 0) or (len(obj.material_slots) <= 1):
            return False
        return True

    def execute(self, context):
        active_object = context.active_object
        active_material = context.object.active_material

        if self.movement == 'TOP':
            dir = 'UP'

            steps = active_object.active_material_index
        else:
            dir = 'DOWN'

            last_slot_index = len(active_object.material_slots) - 1
            steps = last_slot_index - active_object.active_material_index

        if steps == 0:
            self.report({'WARNING'}, active_material.name + " already at " + self.movement.lower() + '!')
        else:
            for i in range(steps):
                bpy.ops.object.material_slot_move(direction = dir)

            self.report({'INFO'}, active_material.name + ' moved to ' + self.movement.lower())

        return {'FINISHED'}


# -----------------------------------------------------------------------------
# menu classes  (To be moved to separate file)

class VIEW3D_MT_materialutilities_assign_material(bpy.types.Menu):
    """Menu for choosing which material should be assigned to current selection"""
    # The menu is filled programmatically with available materials

    bl_idname = "VIEW3D_MT_materialutilities_assign_material"
    bl_label = "Assign Material"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_REGION_WIN'

        bl_id = VIEW3D_OT_materialutilities_assign_material_object.bl_idname
        obj = context.object

        if obj.mode == 'EDIT':
            bl_id = VIEW3D_OT_materialutilities_assign_material_edit.bl_idname

        for material_name in bpy.data.materials.keys():
            layout.operator(bl_id,
                text = material_name,
                icon = 'MATERIAL_DATA').material_name = material_name

        layout.operator(bl_id,
                        text = "Add New Material",
                        icon = 'ADD')


class VIEW3D_MT_materialutilities_select_by_material(bpy.types.Menu):
    """Menu for choosing which material should be used for selection"""
    # The menu is filled programmatically with available materials

    bl_idname = "VIEW3D_MT_materialutilities_select_by_material"
    bl_label = "Select by Material"

    def draw(self, context):
        layout = self.layout

        obj = context.object
        layout.label
        if obj.mode == 'OBJECT':
            #show all used materials in entire blend file
            for material_name, material in bpy.data.materials.items():
                # There's no point in showing materials with 0 users
                #  (It will still show materials with fake user though)
                if material.users > 0:
                    layout.operator(VIEW3D_OT_materialutilities_select_by_material_name.bl_idname,
                                    text = material_name,
                                    icon = 'MATERIAL_DATA',
                                    ).material_name = material_name

        elif obj.mode == 'EDIT':
            #show only the materials on this object
            materials = obj.material_slots.keys()
            for material in materials:
                layout.operator(VIEW3D_OT_materialutilities_select_by_material_name.bl_idname,
                    text = material,
                    icon = 'MATERIAL_DATA').material_name = material

class VIEW3D_MT_materialutilities_clean_slots(bpy.types.Menu):
    """Menu for cleaning up the material slots"""

    bl_idname = "VIEW3D_MT_materialutilities_clean_slots"
    bl_label = "Clean Slots"

    def draw(self, context):
        layout = self.layout

        layout.label
        layout.operator(VIEW3D_OT_materialutilities_clean_material_slots.bl_idname,
                        text = "Clean Material Slots",
                        icon = 'TRASH')
        layout.separator()
        layout.operator(VIEW3D_OT_materialutilities_remove_material_slot.bl_idname,
                        text = "Remove Active Material Slot",
                        icon = 'REMOVE')
        layout.operator(VIEW3D_OT_materialutilities_remove_all_material_slots.bl_idname,
                        text = "Remove All Material Slot",
                        icon = 'CANCEL')


class VIEW3D_MT_materialutilities_select_by_material(bpy.types.Menu):
    """Menu for choosing which material should be used for selection"""
    # The menu is filled programmatically with available materials

    bl_idname = "VIEW3D_MT_materialutilities_select_by_material"
    bl_label = "Select by Material"

    def draw(self, context):
        layout = self.layout

        obj = context.object
        layout.label
        if obj.mode == 'OBJECT':
            #show all used materials in entire blend file
            for material_name, material in bpy.data.materials.items():
                # There's no point in showing materials with 0 users
                #  (It will still show materials with fake user though)
                if material.users > 0:
                    layout.operator(VIEW3D_OT_materialutilities_select_by_material_name.bl_idname,
                                    text = material_name,
                                    icon = 'MATERIAL_DATA',
                                    ).material_name = material_name

        elif obj.mode == 'EDIT':
            #show only the materials on this object
            materials = obj.material_slots.keys()
            for material in materials:
                layout.operator(VIEW3D_OT_materialutilities_select_by_material_name.bl_idname,
                    text = material,
                    icon = 'MATERIAL_DATA').material_name = material

class VIEW3D_MT_materialutilities_specials(bpy.types.Menu):
    """Spcials menu for Material Utilities"""

    bl_idname = "VIEW3D_MT_materialutilities_specials"
    bl_label = "Specials"

    def draw(self, context):
        layout = self.layout

        #layout.operator(VIEW3D_OT_materialutilities_set_new_material_name.bl_idname, icon = "SETTINGS")

        layout.separator()

        layout.operator(MATERIAL_OT_materialutilities_merge_base_names.bl_idname,
                        text = "Merge Base Names",
                        icon = "GREASEPENCIL")


class VIEW3D_MT_materialutilities_main(bpy.types.Menu):
    """Main menu for Material Utilities"""

    bl_idname = "VIEW3D_MT_materialutilities_main"
    bl_label = "Material Utilities"

    def draw(self, context):
        obj = context.object

        layout = self.layout
        layout.operator_context = 'INVOKE_REGION_WIN'

        layout.menu(VIEW3D_MT_materialutilities_assign_material.bl_idname,
                     icon = 'ADD')
        layout.menu(VIEW3D_MT_materialutilities_select_by_material.bl_idname,
                     icon = 'VIEWZOOM')
        layout.separator()

        layout.operator(VIEW3D_OT_materialutilities_copy_material_to_others.bl_idname,
                         text = 'Copy materials to others',
                         icon = 'COPY_ID')

        layout.separator()

        layout.menu(VIEW3D_MT_materialutilities_clean_slots.bl_idname,
                    icon = 'NODE_MATERIAL')

        layout.separator()
        layout.operator(VIEW3D_OT_materialutilities_replace_material.bl_idname,
                        text = 'Replace Material',
                        icon = 'OVERLAY')

        layout.operator(VIEW3D_OT_materialutilities_fake_user_set.bl_idname,
                       text = 'Set Fake User',
                       icon = 'FAKE_USER_OFF')

        layout.operator(VIEW3D_OT_materialutilities_change_material_link.bl_idname,
                       text = 'Change Material Link',
                       icon = 'LINKED')
        layout.separator()

        layout.menu(VIEW3D_MT_materialutilities_specials.bl_idname,
                        icon = 'SOLO_ON')

classes = (
    VIEW3D_OT_materialutilities_assign_material_object,
    VIEW3D_OT_materialutilities_assign_material_edit,
    VIEW3D_OT_materialutilities_select_by_material_name,
    VIEW3D_OT_materialutilities_copy_material_to_others,

    VIEW3D_OT_materialutilities_clean_material_slots,
    VIEW3D_OT_materialutilities_remove_material_slot,
    VIEW3D_OT_materialutilities_remove_all_material_slots,

    VIEW3D_OT_materialutilities_replace_material,
    VIEW3D_OT_materialutilities_fake_user_set,
    VIEW3D_OT_materialutilities_change_material_link,

    MATERIAL_OT_materialutilities_merge_base_names,

    MATERIAL_OT_materialutilities_material_slot_move,

    VIEW3D_MT_materialutilities_assign_material,
    VIEW3D_MT_materialutilities_select_by_material,

    VIEW3D_MT_materialutilities_clean_slots,
    VIEW3D_MT_materialutilities_specials,

    VIEW3D_MT_materialutilities_main,
)

def materialutilities_specials_menu(self, contxt):
    self.layout.separator()
    self.layout.menu(VIEW3D_MT_materialutilities_main.bl_idname)


def materialutilities_menu_move(self, context):
    layout = self.layout
    layout.operator_context = 'INVOKE_REGION_WIN'

    layout.operator(MATERIAL_OT_materialutilities_material_slot_move.bl_idname,
                    icon = 'TRIA_UP_BAR',
                    text = 'Move slot to top').movement = 'TOP'
    layout.operator(MATERIAL_OT_materialutilities_material_slot_move.bl_idname,
                    icon = 'TRIA_DOWN_BAR',
                    text = 'Move slot to bottom').movement = 'BOTTOM'
    layout.separator()

def materialutilities_menu_functions(self, context):
    layout = self.layout
    layout.operator_context = 'INVOKE_REGION_WIN'

    layout.separator()

    layout.menu(VIEW3D_MT_materialutilities_assign_material.bl_idname,
                 icon = 'ADD')
    layout.menu(VIEW3D_MT_materialutilities_select_by_material.bl_idname,
                 icon = 'VIEWZOOM')
    layout.separator()

    layout.separator()

    layout.menu(VIEW3D_MT_materialutilities_clean_slots.bl_idname,
                icon = 'NODE_MATERIAL')

    layout.separator()
    layout.operator(VIEW3D_OT_materialutilities_replace_material.bl_idname,
                    text = 'Replace Material',
                    icon = 'OVERLAY')

    layout.operator(VIEW3D_OT_materialutilities_fake_user_set.bl_idname,
                   text = 'Set Fake User',
                   icon = 'FAKE_USER_OFF')

    layout.operator(VIEW3D_OT_materialutilities_change_material_link.bl_idname,
                   text = 'Change Material Link',
                   icon = 'LINKED')
    layout.separator()

    layout.menu(VIEW3D_MT_materialutilities_specials.bl_idname,
                    icon = 'SOLO_ON')

# This allows you to right click on a button and link to the manual
def materialutilities_manual_map():
    print("ManMap")
    url_manual_prefix = "https://github.com/ChrisHinde/MaterialUtils/"
    url_manual_map = []
    #url_manual_mapping = ()
        #("bpy.ops.view3d.materialutilities_*", ""),
        #("bpy.ops.view3d.materialutilities_assign_material_edit", ""),
        #("bpy.ops.view3d.materialutilities_select_by_material_name", ""),)

    for cls in classes:
        if issubclass(cls, bpy.types.Operator):
            url_manual_map.append(("bpy.ops." + cls.bl_idname, ""))

    url_manual_mapping = tuple(url_manual_map)
    #print(url_manual_mapping)
    return url_manual_prefix, url_manual_mapping

register, unregister = bpy.utils.register_classes_factory(classes)


def mu_register():
    """Register the classes of Material Utilities together with the default shortcut (Shift+Q)"""
    register()

    bpy.types.VIEW3D_MT_object_context_menu.append(materialutilities_specials_menu)

    bpy.types.MATERIAL_MT_context_menu.prepend(materialutilities_menu_move)
    bpy.types.MATERIAL_MT_context_menu.append(materialutilities_menu_functions)

    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name = "3D View", space_type = "VIEW_3D")
        kmi = km.keymap_items.new('wm.call_menu', 'Q', 'PRESS', ctrl = False, shift = True)
        kmi.properties.name = VIEW3D_MT_materialutilities_main.bl_idname

        bpy.utils.register_manual_map(materialutilities_manual_map)


def mu_unregister():
    """Unregister the classes of Material Utilities together with the default shortcut for the menu"""
    unregister()

    bpy.utils.unregister_manual_map(materialutilities_manual_map)

    bpy.types.VIEW3D_MT_object_context_menu.remove(materialutilities_specials_menu)

    bpy.types.MATERIAL_MT_context_menu.remove(materialutilities_menu_move)
    bpy.types.MATERIAL_MT_context_menu.remove(materialutilities_menu_functions)

    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps["3D View"]
        for kmi in km.keymap_items:
            if kmi.idname == 'wm.call_menu':
                if kmi.properties.name == VIEW3D_MT_materialutilities_main.bl_idname:
                    km.keymap_items.remove(kmi)
                    break

#if __name__ == "__main__":
#    mu_register()

print("MU Start!")
mu_register()
