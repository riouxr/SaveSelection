import bpy
import os

def get_selected_collections(context):
    """
    Uses a temporary override to obtain selected collections from the Outliner.
    Returns a list of bpy.types.Collection that are both selected and visible.
    """
    selected = []
    outliner_area = next((area for area in context.window.screen.areas if area.type == 'OUTLINER'), None)
    if outliner_area:
        region = next((r for r in outliner_area.regions if r.type == 'WINDOW'), None)
        with context.temp_override(window=context.window, screen=context.screen, area=outliner_area, region=region):
            if hasattr(bpy.context, "selected_ids"):
                for id_item in bpy.context.selected_ids:
                    if isinstance(id_item, bpy.types.Collection) and not id_item.hide_viewport:
                        selected.append(id_item)
    return selected

def find_parent_collection(target, current):
    """
    Recursively search for the parent of 'target' starting from 'current'.
    Returns the parent collection if found, or None otherwise.
    """
    for child in current.children:
        if child == target:
            return current
        result = find_parent_collection(target, child)
        if result is not None:
            return result
    return None

def create_temp_scene(name="TempExportScene"):
    """
    Create the empty scene used to hold the export.

    Deliberately NOT bpy.data.scenes.new(): a scene built that way crashes
    bpy.data.libraries.write() in Blender 5.2 (EXCEPTION_ACCESS_VIOLATION), even
    when the scene is completely empty. Copying an existing scene produces one the
    writer accepts, so we copy the current scene and strip it back to empty.

    Everything that could drag unrelated datablocks into the export (camera, world,
    sequence editor, markers, compositor tree, linked collections/objects) is cleared,
    so the result is equivalent to a fresh scene apart from render settings.
    """
    temp_scene = bpy.context.scene.copy()
    temp_scene.name = name

    # Drop pointers that would otherwise pull in unwanted dependencies.
    temp_scene.camera = None
    temp_scene.world = None
    for clear in (temp_scene.sequence_editor_clear, temp_scene.timeline_markers.clear):
        try:
            clear()
        except Exception:
            pass
    for attr in ("node_tree", "compositing_node_group"):
        if hasattr(temp_scene, attr):
            try:
                setattr(temp_scene, attr, None)
            except Exception:
                pass

    # Empty the master collection: the copy starts out sharing the source scene's contents.
    temp_root = temp_scene.collection
    for child in list(temp_root.children):
        temp_root.children.unlink(child)
    for obj in list(temp_root.objects):
        temp_root.objects.unlink(obj)

    return temp_scene


def save_selected_mesh(filepath, place_origin=False, zero_rot=False, unit_scale=False):
    # Automatically add .blend extension if it's missing.
    if not filepath.lower().endswith('.blend'):
        filepath += '.blend'
    
    # 1. Gather selected objects and collections.
    sel_objs = list(bpy.context.selected_objects)
    sel_colls = get_selected_collections(bpy.context)
    # Filter: keep only collections that contain at least one selected object.
    valid_colls = [coll for coll in sel_colls if any(coll.objects.get(obj.name) is not None for obj in sel_objs)]
    
    if not sel_objs and not valid_colls:
        print("No valid objects or collections selected!")
        return {'CANCELLED'}
    
    # 2. Record original names for valid collections.
    orig_names = {coll: coll.name for coll in valid_colls}
    
    # 3. Create a temporary scene.
    temp_scene = create_temp_scene()
    temp_root = temp_scene.collection  # Root collection of the temporary scene.
    
    # 4. In the original file, rename each valid collection by appending "_temp".
    for coll in valid_colls:
        coll.name = coll.name + "_temp"
    
    # 5. In the temporary scene, duplicate each valid collection.
    # First pass: create duplicate for each valid collection and link to temp_root.
    dup_coll_mapping = {}
    for coll in valid_colls:
        desired_name = orig_names[coll]
        dup_coll = bpy.data.collections.new("")
        dup_coll.name = desired_name  # Force its name to the original name.
        dup_coll_mapping[coll] = dup_coll
        temp_root.children.link(dup_coll)
        # Link selected objects from the original collection.
        for obj in coll.objects:
            if obj in sel_objs:
                try:
                    dup_coll.objects.link(obj)
                except RuntimeError:
                    pass
                        
    # 6. Re-establish hierarchy in the temporary scene.
    # Use the working file's root as the starting point.
    original_root = bpy.context.scene.collection
    for coll in valid_colls:
        # Find parent in the working file hierarchy.
        parent = find_parent_collection(coll, original_root)
        if parent and parent in valid_colls:
            # If the parent is valid, reassign duplicate's parent.
            child_dup = dup_coll_mapping[coll]
            parent_dup = dup_coll_mapping[parent]
            # Unlink child from temp_root if necessary.
            try:
                temp_root.children.unlink(child_dup)
            except Exception:
                pass
            parent_dup.children.link(child_dup)
    # 7. For any selected object not already in a duplicate, link it directly to temp_root.
    for obj in sel_objs:
        in_dup = any(dup.objects.get(obj.name) is not None for dup in dup_coll_mapping.values())
        if not in_dup:
            try:
                temp_root.objects.link(obj)
            except RuntimeError:
                pass
                    
    # 8. Build the set of datablocks to export.
    # temp_scene.collection is the scene's embedded master collection, not a standalone
    # datablock, so it isn't listed here; writing temp_scene carries it along anyway.
    # Selected objects are listed explicitly rather than left to scene traversal.
    datablocks = {temp_scene} | set(dup_coll_mapping.values()) | set(sel_objs)

    # Store original transforms so we can restore them after export
    original_transforms = {}
    try:
        # === Apply transform options if requested ===
        if place_origin or zero_rot or unit_scale:
            for obj in temp_scene.objects:
                if obj.type in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'GPENCIL', 'ARMATURE', 'LATTICE', 'EMPTY'}:
                    # Store original values
                    original_transforms[obj] = {
                        'location': obj.location.copy(),
                        'rotation_euler': obj.rotation_euler.copy() if hasattr(obj, 'rotation_euler') else None,
                        'rotation_quaternion': obj.rotation_quaternion.copy() if hasattr(obj, 'rotation_quaternion') else None,
                        'scale': obj.scale.copy()
                    }
                    # Apply requested transforms
                    if place_origin:
                        obj.location = (0.0, 0.0, 0.0)
                    if zero_rot:
                        if hasattr(obj, 'rotation_euler'):
                            obj.rotation_euler = (0.0, 0.0, 0.0)
                        if hasattr(obj, 'rotation_quaternion'):
                            obj.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
                    if unit_scale:
                        obj.scale = (1.0, 1.0, 1.0)

        bpy.data.libraries.write(filepath, datablocks=datablocks, path_remap='RELATIVE')
    finally:
        # Always undo our edits to the working file, even if the export failed, so a
        # failed export can't leave behind "_temp" collection names or a stray scene.

        # Restore original transforms
        for obj, transforms in original_transforms.items():
            obj.location = transforms['location']
            if transforms['rotation_euler'] is not None:
                obj.rotation_euler = transforms['rotation_euler']
            if transforms['rotation_quaternion'] is not None:
                obj.rotation_quaternion = transforms['rotation_quaternion']
            obj.scale = transforms['scale']

        # 9. Cleanup: Remove the temporary scene.
        bpy.data.scenes.remove(temp_scene)

        # Optionally, remove any duplicate collections that linger (should be removed with the scene).
        for dup in dup_coll_mapping.values():
            try:
                bpy.data.collections.remove(dup)
            except Exception as e:
                print(f"Couldn't remove duplicate collection {dup.name}: {e}")

        # 10. Restore original collection names in the working file.
        for coll, orig_name in orig_names.items():
            coll.name = orig_name

    print(f"Exported selection to {filepath}")
    return {'FINISHED'}
