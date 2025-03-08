bl_info = {
    "name": "Save Selection as .blend",
    "author": "Blender Bob",
    "version": (1, 0, 1),
    "blender": (3, 2, 0),
    "location": "File > Export > Save Selection",
    "description": "Saves only the selected objects to a new .blend file.",
    "category": "Import-Export",
}

import bpy
from .save_selection import save_selected_mesh

# Define the operator
class EXPORT_OT_save_selection(bpy.types.Operator):
    """Save only selected objects as a .blend file"""
    bl_idname = "export.save_selection"
    bl_label = "Save Selection"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        save_selected_mesh(self.filepath)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# Register menu function
def menu_func(self, context):
    self.layout.operator(EXPORT_OT_save_selection.bl_idname, text="Save Selection (.blend)")

# Register classes
def register():
    bpy.utils.register_class(EXPORT_OT_save_selection)
    bpy.types.TOPBAR_MT_file_export.append(menu_func)

def unregister():
    bpy.utils.unregister_class(EXPORT_OT_save_selection)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)

if __name__ == "__main__":
    register()
