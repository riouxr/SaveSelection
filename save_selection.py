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

def save_selected_mesh(filepath):
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
    temp_scene = bpy.data.scenes.new("TempExportScene")
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
    datablocks = {temp_scene, temp_root} | set(dup_coll_mapping.values())
    
    bpy.data.libraries.write(filepath, datablocks=datablocks, path_remap='RELATIVE')
    
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
        if coll.name.endswith("_temp"):
            coll.name = orig_name
        else:
            coll.name = orig_name
            
    print(f"Exported selection to {filepath}")
    return {'FINISHED'}

# Example usage:
# save_selected_mesh("I:/path/to/exported_file.blend")
