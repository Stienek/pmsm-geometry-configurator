from femm import *
import sys, os, shutil
import numpy as np
import shutil

sys.path.insert(0, os.getcwd())
from modules.fem_util import *

def bdnry():
    return [[0.1, 5], [0.01, 0.99]]

def create(params):
    if "magnet_depth" not in params:
        raise KeyError("Parameter Dict did not contain magnet_depth")
    else:
        magnet_depth = params["magnet_depth"]
    if "ratio" not in params:
        raise KeyError("Parameter Dict did not contain ratio")
    else:
        ratio = params["ratio"]
    if "halbach_side" not in params:
        halbach_side = "A"
    else:
        halbach_side = params["halbach_side"]
    halbach_angle = 90 if halbach_side == "A" else -90
    
    if magnet_depth < bdnry()[0][0]:
        magnet_depth = bdnry()[0][0]
    elif magnet_depth > bdnry()[0][1]:
        magnet_depth = bdnry()[0][1]
    if ratio < bdnry()[1][0]:
        ratio = bdnry()[1][0]
    elif ratio > bdnry()[1][1]:
        ratio = bdnry()[1][1]
    angle_per_pole = 90/2
    angle_quer = angle_per_pole*ratio
    angle_straight = angle_per_pole - angle_quer
    angle_precision = 300
    segments_quer = int(angle_quer/angle_precision)
    segments_quer_half = int(segments_quer/2)
    segments_straight = int(angle_straight/angle_precision)
    drawTangentialMagnet(outer_radius-magnet_depth, outer_radius, 0, angle_quer/2, 0, angle_quer/2, segments=segments_quer_half, material="N28UH", magdir=-halbach_angle,draw_first=False, draw_last=False, group=11)
    drawTangentialMagnet(outer_radius-magnet_depth, outer_radius, angle_quer/2, angle_quer/2 + angle_straight, angle_quer/2, angle_quer/2 + angle_straight, segments=segments_straight, material="N28UH", magdir=180, group=12)
    drawTangentialMagnet(outer_radius-magnet_depth, outer_radius, angle_quer/2 + angle_straight, angle_quer*3/2 + angle_straight, angle_quer/2 + angle_straight, angle_quer*3/2 + angle_straight, segments=segments_quer, material="N28UH", magdir=halbach_angle, draw_first=False, draw_last=False, group=13) 
    drawTangentialMagnet(outer_radius-magnet_depth, outer_radius, angle_quer*3/2 + angle_straight, angle_quer*3/2 + 2*angle_straight, angle_quer*3/2 + angle_straight, angle_quer*3/2 + 2*angle_straight, segments=segments_straight, material="N28UH", magdir=0, group=14)  
    drawTangentialMagnet(outer_radius-magnet_depth, outer_radius, angle_quer*3/2 + 2*angle_straight, angle_quer*2 + 2*angle_straight, angle_quer*3/2 + 2*angle_straight, angle_quer*2 + 2*angle_straight, segments=segments_quer_half, material="N28UH", magdir=-halbach_angle, draw_first=False, draw_last=False, group=11) 
    hlfdepth = (outer_radius-magnet_depth-inner_radius)/2 + inner_radius
    drawLabel(hlfdepth*np.cos(np.pi/4), hlfdepth*np.sin(np.pi/4), material="50JN400", group=5)   
    mi_clearselected()
    mi_selectsegment(0, outer_radius-magnet_depth/2)
    mi_selectsegment(outer_radius-magnet_depth/2, 0)
    mi_setsegmentprop("PeriodicRotor05", 0, 1, 0, 5)
    
    return {"angle":0, 'x':magnet_depth, 'y':ratio}

if __name__ == "__main__":
    openfemm()
    if os.path.exists("tmp.fem"):
        os.remove("tmp.fem")
    shutil.copyfile("stator_quater.FEM", "tmp.fem")
    opendocument("tmp.fem")
    drawLine(0, 0, outer_radius, 0)
    drawLine(0, 0, 0, outer_radius)
    drawArc(outer_radius, 0, 0, outer_radius, 90)
    create({'magnet_depth':3, 'ratio':0.2, 'halbach_side':'B'})
    input()
    closefemm()
    sys.exit(0) 
