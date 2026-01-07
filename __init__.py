bl_info = {
    "name": "Save Selection as .blend",
    "author": "Blender Bob",
    "version": (1, 0, 5),
    "blender": (4, 2, 0),
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

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "place_origin")
        layout.prop(self, "zero_rot")
        layout.prop(self, "unit_scale")


    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    place_origin: bpy.props.BoolProperty(
        name="Place at Origin",
        description="Move exported objects to world origin (0,0,0)",
        default=False,
        options={'SKIP_SAVE'}
    )

    zero_rot: bpy.props.BoolProperty(
        name="Set Rotations to 0",
        description="Clear rotation on exported objects",
        default=False,
        options={'SKIP_SAVE'}
    )

    unit_scale: bpy.props.BoolProperty(
        name="Set Scale to 1",
        description="Reset scale on exported objects",
        default=False,
        options={'SKIP_SAVE'}
    )


    def execute(self, context):
        save_selected_mesh(self.filepath, place_origin=self.place_origin, zero_rot=self.zero_rot, unit_scale=self.unit_scale)
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
