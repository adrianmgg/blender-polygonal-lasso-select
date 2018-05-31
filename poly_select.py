import bpy
import bgl
import blf
from bpy_extras import view3d_utils
from mathutils.geometry import intersect_line_line_2d
from mathutils import Vector
import bmesh

bl_info = {
    "name": "Polygonal Lasso Select",
    "category": "User Interface",
    "author": "Adrian Guerra",
    "description": "adds a polygonal lasso select tool",
    "warning": "not stable, expect script to crash sometimes",
    "version": (1,2)
}

def draw_callback_px(self, context):

    font_id = 0  # XXX, need to find out how best to get this.

    # draw some text
    blf.position(font_id, 15, 30, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, str(self.mouse_pos[0])+','+str(self.mouse_pos[1]))      
    # 50% alpha, 2 pixel width line
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 1.0, 0.0, 0.5)
    bgl.glLineWidth(2)
    bgl.glBegin(bgl.GL_LINE_STRIP)
    for x,y in self.poly_points:
        bgl.glVertex2i(x,y)
    bgl.glColor4f(1.0, 0.0, 0.0, 0.5)
    bgl.glVertex2i(self.mouse_pos[0],self.mouse_pos[1])
    bgl.glEnd()
    bgl.glPointSize(4.0)
    bgl.glBegin(bgl.GL_POINTS)
    bgl.glColor4f(0.0, 1.0, 1.0, 0.5)
    for obj,point in self.visible_objects:
        bgl.glVertex2f(point[0],point[1])
    for vert,point in self.verts:
        bgl.glVertex2f(point[0],point[1])
    bgl.glEnd()
    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)

class PolyLassoOperator(bpy.types.Operator):
    """Polygonal lasso select tool"""
    bl_idname = "view3d.poly_select"
    bl_label = "Poly Select"

    def handle_click(self):
        self.poly_points.append([self.mouse_pos[0],self.mouse_pos[1]])
        
    def closed_check(self,tolerance):
        if len(self.poly_points)<=3:
            return False
        pt1=self.poly_points[0]
        pt2=self.poly_points[-1]
        diffx=abs((pt1[0]-pt2[0])/2)
        diffy=abs((pt1[1]-pt2[1])/2)
        print(str(diffx)+','+str(diffy))
        return diffx<=tolerance and diffy<=tolerance

    def checkpt(self,point2d):
        intersections=0
        for i in range(len(self.poly_points)):
            pt1=self.poly_points[i]
            pt2=self.poly_points[(i+1)%len(self.poly_points)]
            intersect=intersect_line_line_2d(Vector(point2d),Vector([point2d[0],0]),Vector(pt1),Vector(pt2))
            if intersect!=None:
                intersections+=1
        return intersections%2!=0

    def select_objects(self):
        for obj,center in self.visible_objects:
            if self.checkpt(center):
                obj.select=True
        for vert,pos in self.verts:
            if self.checkpt(pos):
                vert.select=True
    


    def modal(self, context, event):
        context.area.tag_redraw()
        if event.type == 'MOUSEMOVE':
            self.mouse_pos=[event.mouse_region_x, event.mouse_region_y]

        elif event.type == 'LEFTMOUSE':
            self.handle_click()
            if self.closed_check(2):
                self.select_objects()
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}


    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            self.visible_objects=[]#rename to objects or something
            self.verts=[]
            self.bm=None
            viewport = context.area.regions[4]
            def point3dto2d(point3d):
                for space in context.area.spaces:
                    print(space.type)
                point2d = view3d_utils.location_3d_to_region_2d(viewport,context.area.spaces[0].region_3d,point3d)
                point2dshifted = point2d[0]+context.window.x, point2d[1]+context.window.x
                return point2dshifted
            if context.mode=='OBJECT':
                for visobj in bpy.context.visible_objects:
                    origin=visobj.location
                    self.visible_objects.append([visobj,point3dto2d(origin)])
            if context.mode=='EDIT_MESH':
                activeobj=context.active_object
                mesh=bmesh.from_edit_mesh(activeobj.data)
                self.bm=mesh
                for vert in mesh.verts:
                    worldpos=activeobj.matrix_world*vert.co
                    self.verts.append([vert,point3dto2d(worldpos)])
            # the arguments we pass the the callback
            args = (self, context)
            # Add the region OpenGL drawing callback
            # draw in view space with 'POST_VIEW' and 'PRE_VIEW'
            self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
            self.mouse_pos = [0,0]
            self.poly_points = []

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}


def register():
    bpy.utils.register_class(PolyLassoOperator)


def unregister():
    bpy.utils.unregister_class(PolyLassoOperator)

if __name__ == "__main__":
    register()
