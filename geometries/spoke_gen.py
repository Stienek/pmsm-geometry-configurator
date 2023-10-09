from femm import *
import sys, os, shutil
import numpy as np

sys.path.insert(0, os.getcwd())
from modules.fem_util import *

mag_angle_deg = 6

def bdnry():
    return [0.1, 2*np.sin(np.deg2rad(45/2))*inner_radius]

def create(params):
    if "magnet_depth" not in params:
        raise KeyError("Parameter Dict did not contain magnet_depth")
    else:
        magnet_depth = params["magnet_depth"]
    if magnet_depth < bdnry()[0]:
        magnet_depth = bdnry()[0]
    elif magnet_depth > bdnry()[1]:
        magnet_depth = bdnry()[1]
    
    if "outer_radius"  in params:
        outer_radius = params["outer_radius"]
    else:
        outer_radius = 16.1

    magnet_width = magnet_depth
    magnet_inset = arcDepth(outer_radius, magnet_width)
    magnet_inset_inside = arcDepth(inner_radius, magnet_width)
    magnet_length = outer_radius - inner_radius + magnet_inset_inside

    drawLine(inner_radius - magnet_inset_inside, magnet_width/2, outer_radius - magnet_inset, magnet_width/2)
    drawLine(inner_radius - magnet_inset_inside, 0, inner_radius - magnet_inset_inside, magnet_width/2)
    drawLabel(outer_radius - magnet_width/2, magnet_width/4, material="N28UH", magdir=-90, group=11)
    
    drawLine(magnet_width/2, inner_radius - magnet_inset_inside, magnet_width/2, outer_radius - magnet_inset)
    drawLine(0, inner_radius - magnet_inset_inside, magnet_width/2, inner_radius - magnet_inset_inside)
    drawLabel(magnet_width/4, outer_radius - magnet_width/2, material="N28UH", magdir=0, group=12)

    
    drawLine(magnet_width/2, -(inner_radius - magnet_inset_inside), magnet_width/2, -(outer_radius - magnet_inset))
    drawLine(-magnet_width/2, -(inner_radius - magnet_inset_inside), -magnet_width/2, -(outer_radius - magnet_inset))
    drawLine(-magnet_width/2, -(inner_radius - magnet_inset_inside), magnet_width/2, -(inner_radius - magnet_inset_inside))
    
    mi_clearselected()
    mi_selectrectangle(-magnet_width/2, -(inner_radius - magnet_inset_inside), magnet_width/2, -(outer_radius - magnet_inset), 4) # Four means Select EVERYTHING
    mi_moverotate(0, 0, 135)
    drawLabel(np.cos(np.deg2rad(45))*((outer_radius-inner_radius)/2 + inner_radius), np.sin(np.deg2rad(45))*((outer_radius-inner_radius)/2 + inner_radius), material="N28UH", magdir=135, group=13)

    mi_clearselected()
    mi_selectarcsegment(np.cos(np.deg2rad(0))*(inner_radius), np.sin(np.deg2rad(0))*(inner_radius))
    mi_selectarcsegment(np.cos(np.deg2rad(45))*(inner_radius), np.sin(np.deg2rad(45))*(inner_radius))
    mi_selectarcsegment(np.cos(np.deg2rad(90))*(inner_radius), np.sin(np.deg2rad(90))*(inner_radius))
    mi_selectnode(0, inner_radius)
    mi_selectnode(inner_radius, 0)
    mi_deleteselected()
    drawLine(inner_radius - magnet_inset_inside, 0, outer_radius, 0, bdry="PeriodicRotor02")
    drawLine(0, inner_radius - magnet_inset_inside, 0, outer_radius, bdry="PeriodicRotor02")

    drawLabel(np.cos(np.deg2rad(45/2))*((outer_radius-inner_radius)/2 + inner_radius), np.sin(np.deg2rad(45/2))*((outer_radius-inner_radius)/2 + inner_radius), material="50JN400", group=5)
    drawLabel(np.cos(np.deg2rad(45/2 + 45))*((outer_radius-inner_radius)/2 + inner_radius), np.sin(np.deg2rad(45/2+45))*((outer_radius-inner_radius)/2 + inner_radius), material="50JN400", group=5)
    
    return {"magnet_width":magnet_length, "magnet_depth":magnet_width}

if __name__ == "__main__":
    openfemm()
    if os.path.exists("tmp.fem"):
        os.remove("tmp.fem")
    shutil.copyfile("stator_quater.FEM", "tmp.fem")
    opendocument("tmp.fem")
    drawLine(0, 0, outer_radius, 0)
    drawLine(0, 0, 0, outer_radius)
    drawArc(outer_radius, 0, 0, outer_radius, 90)
    create({'magnet_depth':3})
    input()
    closefemm()
    sys.exit(0)
