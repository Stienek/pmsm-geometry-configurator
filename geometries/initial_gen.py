from femm import *
import sys, os, shutil
import numpy as np

sys.path.insert(0, os.getcwd())
from modules.fem_util import *

mag_angle_deg = 6

def bdnry():
    return [0.1 + arcDepth(outer_radius, 0, outer_radius*np.cos(np.deg2rad(45 - mag_angle_deg)),outer_radius*np.sin(np.deg2rad(45 - mag_angle_deg)), 45 - mag_angle_deg)[0], outer_radius/2] # 3 Degrees distance between magnets.

def create(params):
    if "magnet_depth" not in params:
        raise KeyError("Parameter Dict did not contain magnet_depth")
    else:
        magnet_depth = params["magnet_depth"]
        
    if magnet_depth < bdnry()[0]:
        magnet_depth = bdnry()[0]
    elif magnet_depth > bdnry()[1]:
        magnet_depth = bdnry()[1]

    angle_total = 45 - mag_angle_deg
    h1 = outer_radius/np.cos(np.deg2rad(angle_total/2))
    h2 = magnet_depth/np.cos(np.deg2rad(angle_total/2))
    h3 = h1 - h2
    g4 = h3*np.sin(np.deg2rad(angle_total/2))
    magnet_width = 2*g4
    drawSurfaceMagnet(magnet_width, magnet_depth, angle=45/2, group=11, material="N28UH", magdir=-180+angle_total/2)
    drawSurfaceMagnet(magnet_width, magnet_depth, angle=45+45/2, group=12, material="N28UH", magdir=45+angle_total/2)
    drawLabel(outer_radius/2, outer_radius/2, material="50JN400", group=5)

    return {"magnet_width":magnet_width, "magnet_depth":magnet_depth}

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
