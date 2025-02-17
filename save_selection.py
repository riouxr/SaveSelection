import bpy

# -------------------------------------------------------------------
#   Get Selected and Visible Collections from the Outliner
# -------------------------------------------------------------------
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

# -------------------------------------------------------------------
#   Export Only Selected, Visible Objects and Collections
# -------------------------------------------------------------------
def save_selected_mesh(filepath):
    selected_objects = set(bpy.context.selected_objects)  # Store selected objects
    selected_collections = get_selected_collections(bpy.context)  # Get selected & visible collections

    # Filter collections: Only include those that contain selected objects
    valid_collections = {}
    for collection in selected_collections:
        objects_in_collection = [obj for obj in collection.objects if obj in selected_objects]
        if objects_in_collection:  # Keep only collections with selected objects
            valid_collections[collection] = objects_in_collection

    # Add collection objects to selection
    for collection_objs in valid_collections.values():
        selected_objects.update(collection_objs)

    if not selected_objects:
        print("No objects or valid collections selected!")
        return {'CANCELLED'}

    # Store the original scene
    original_scene = bpy.context.window.scene

    # Create a new temporary scene
    temp_scene = bpy.data.scenes.new("TempExportScene")

    # Create new collections in the temporary scene and maintain hierarchy
    collection_mapping = {}
    for collection, objects in valid_collections.items():
        new_collection = bpy.data.collections.new(collection.name)  # Duplicate collection
        temp_scene.collection.children.link(new_collection)  # Link to the temp scene
        collection_mapping[collection] = new_collection  # Store mapping

    # Link selected objects to the appropriate collections in the temp scene
    for obj in selected_objects:
        linked = False
        for collection in obj.users_collection:
            if collection in collection_mapping:
                collection_mapping[collection].objects.link(obj)  # Link to the duplicate collection
                linked = True
                break
        if not linked:  # If object was not in a selected collection, add to main scene collection
            temp_scene.collection.objects.link(obj)

    # Set the temporary scene as active
    bpy.context.window.scene = temp_scene

    # Save the file (only objects in the temporary scene will be saved)
    bpy.ops.wm.save_as_mainfile(filepath=filepath, copy=True)

    # Restore the original scene
    bpy.context.window.scene = original_scene

    # Remove the temporary scene
    bpy.data.scenes.remove(temp_scene)

    print(f"File saved with selected objects and valid, visible collections: {filepath}")
    return {'FINISHED'}
