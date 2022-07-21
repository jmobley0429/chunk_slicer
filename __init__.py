bl_info = {
    "name": "Chunk Slicer",
    "description": "Slices an object into uniform chunks on selected axes.",
    "author": "Jake Mobley",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "Operator Search > Chunk Slicer",
    "category": "Modeling",
    "tracker_url": "https://github.com/jmobley0429/chunk_slicer/issues",
    "doc_url": "https://github.com/jmobley0429/chunk_slicer/blob/master/README.md",
}


if "bpy" in locals():
    import importlib

    importlib.reload(chunk_slicer)
else:
    import bpy
    from . import chunk_slicer

addon_keymaps = []


def register():
    bpy.utils.register_class(chunk_slicer.OBJECT_OT_chunk_slicer)

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


def unregister_keymaps(addon_keymaps):
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        for km, kmi in addon_keymaps:
            km.keymap_items.remove(kmi)
            kc.keymaps.remove(km)
    addon_keymaps.clear()


def unregister():
    bpy.utils.unregister_class(chunk_slicer.OBJECT_OT_chunk_slicer)
    unregister_keymaps(addon_keymaps)


if __name__ == "__main__":
    register()
