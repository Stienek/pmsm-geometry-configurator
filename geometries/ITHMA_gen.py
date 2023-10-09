from femm import *
import sys, os
import numpy as np
import shutil

sys.path.insert(0, os.getcwd())
from modules.fem_util import *

def bdnry():
    return [[0.1, 5], [0.01, 0.89], [0, 0.1]]

def create(params):
    if "magnet_depth" not in params:
        raise KeyError("Parameter Dict did not contain magnet_depth")
    else:
        magnet_depth = params["magnet_depth"]
    
    if "halbach_side" not in params:
        halbach_side = "A"
    else:
        halbach_side = params["halbach_side"]

    if 'create_by_angle' not in params:
        create_by_angle = False
    else:
        create_by_angle = params['create_by_angle']

    
    mid_radius = (outer_radius + inner_radius)/2
    dradius = np.abs(outer_radius - inner_radius)
    npole = 8
    if create_by_angle:
        if "ratio" not in params:
            raise KeyError("Parameter Dict did not contain ratio_inner")
        else:
            ratio = params["ratio"]
        if "angle" not in params:
            raise KeyError("Parameter Dict did not contain ratio_outer")
        else:
            angle = params["angle"]
        
        dr = (dradius*npole)/(2*np.pi*mid_radius)*1/(np.tan(np.deg2rad(90-angle)))
        ratio_inner = ratio + dr/2
        ratio_outer = ratio - dr/2
    else:
        if "ratio_inner" not in params:
            raise KeyError("Parameter Dict did not contain ratio_inner")
        else:
            ratio_inner = params["ratio_inner"]
        if "ratio_outer" not in params:
            raise KeyError("Parameter Dict did not contain ratio_outer")
        else:
            ratio_outer = params["ratio_outer"]

        dratio = np.abs(ratio_outer - ratio_inner)
        ratio = (ratio_inner + ratio_outer)/2
        angle = (1 if ratio_inner>ratio_outer else -1)*(90-(np.rad2deg(np.arctan(dradius/(2*np.pi*mid_radius/npole*dratio))) if dratio != 0 else 90))


    halbach_angle = 90 if halbach_side == "A" else -90
    angle_per_pole = 90/2
    angle_quer_outer = angle_per_pole*ratio_outer
    angle_straight_outer = angle_per_pole - angle_quer_outer
    angle_quer_inner = angle_per_pole*ratio_inner
    angle_straight_inner = angle_per_pole - angle_quer_inner

    if 'magangle' not in params:
        p1 = np.array([outer_radius-magnet_depth/2, 0])
        p2 = np.array([(outer_radius-magnet_depth*3/4)*np.cos(-1*np.deg2rad((angle_quer_inner + angle_quer_outer)/4)), (outer_radius-magnet_depth*3/4)*np.sin(-1*np.deg2rad((angle_quer_inner + angle_quer_outer)/4))])
        d1 = p1 - p2
        angle_degrees = np.rad2deg(np.abs(np.arctan(np.abs(d1[0])/np.abs(d1[1]))))
        angle_degrees = angle_degrees if halbach_side == 'A' else -angle_degrees
    else:
        angle_degrees = params['magangle']
    

    angle_precision = 300
    segments_quer = int(max(angle_quer_inner, angle_quer_outer)/angle_precision)
    segments_quer_half = int(segments_quer/2)
    segments_straight = int(max(angle_straight_inner, angle_straight_outer)/angle_precision)
    drawTangentialMagnet(outer_radius-magnet_depth, outer_radius, 0, angle_quer_inner/2, 0, angle_quer_outer/2, segments=segments_quer_half, material="N28UH", magdir=-halbach_angle-angle_degrees,draw_first=False, draw_last=False, group=11)
    drawTangentialMagnet(outer_radius-magnet_depth, outer_radius, angle_quer_inner/2, angle_quer_inner/2 + angle_straight_inner, angle_quer_outer/2, angle_quer_outer/2 + angle_straight_outer, segments=segments_straight, material="N28UH", magdir=180, group=12)
    drawTangentialMagnet(outer_radius-magnet_depth, outer_radius, angle_quer_inner/2 + angle_straight_inner, angle_per_pole, angle_quer_outer/2 + angle_straight_outer, angle_per_pole, segments=segments_quer_half, material="N28UH", magdir=halbach_angle+angle_degrees, draw_first=False, draw_last=True, group=13) 
    drawTangentialMagnet(outer_radius-magnet_depth, outer_radius, angle_per_pole, angle_quer_inner*3/2 + angle_straight_inner, angle_per_pole, angle_quer_outer*3/2 + angle_straight_outer, segments=segments_quer_half, material="N28UH", magdir=halbach_angle-angle_degrees, draw_first=False, draw_last=False, group=13) 
    drawTangentialMagnet(outer_radius-magnet_depth, outer_radius, angle_quer_inner*3/2 + angle_straight_inner, angle_quer_inner*3/2 + 2*angle_straight_inner, angle_quer_outer*3/2 + angle_straight_outer, angle_quer_outer*3/2 + 2*angle_straight_outer, segments=segments_straight, material="N28UH", magdir=0, group=14)  
    drawTangentialMagnet(outer_radius-magnet_depth, outer_radius, angle_quer_inner*3/2 + 2*angle_straight_inner, angle_quer_inner*2 + 2*angle_straight_inner, angle_quer_outer*3/2 + 2*angle_straight_outer, angle_quer_outer*2 + 2*angle_straight_outer, segments=segments_quer_half, material="N28UH", magdir=-halbach_angle+angle_degrees, draw_first=False, draw_last=False, group=11) 
    hlfdepth = (outer_radius-magnet_depth-inner_radius)/2 + inner_radius
    drawLabel(hlfdepth*np.cos(np.pi/4), hlfdepth*np.sin(np.pi/4), material="50JN400", group=5)   
    mi_clearselected()
    mi_selectsegment(0, outer_radius-magnet_depth/2)
    mi_selectsegment(outer_radius-magnet_depth/2, 0)
    mi_setsegmentprop("PeriodicRotor05", 0, 1, 0, 5)
    
    return {'ratio_inner':ratio_inner, 'ratio_outer':ratio_outer, 'ratio':ratio, 'angle':angle, 'magangle':angle_degrees, 'x':angle, 'y':angle_degrees}

if __name__ == "__main__":
    openfemm()
    if os.path.exists("tmp.fem"):
        os.remove("tmp.fem")
    shutil.copyfile("stator_quater.FEM", "tmp.fem")
    opendocument("tmp.fem")
    drawLine(0, 0, outer_radius, 0)
    drawLine(0, 0, 0, outer_radius)
    drawArc(outer_radius, 0, 0, outer_radius, 90)
    create({'magnet_depth':3, 'ratio':0.1, 'angle':-8, 'magangle':-10, 'halbach_side':'B', 'create_by_angle': True})
    input()
    closefemm()
    sys.exit(0) 
