if "bpy" in locals():
    import importlib

    importlib.reload(chunk_slicer)
else:
    from my_addons.chunk_slicer import OBJECT_OT_chunk_slicer


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
