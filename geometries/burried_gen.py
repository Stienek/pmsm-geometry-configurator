from femm import *
import sys, os, shutil
import numpy as np

sys.path.insert(0, os.getcwd())
from modules.fem_util import *

mag_angle_deg = 6

def create(params):
    if "magnet_depth" not in params:
        raise KeyError("Parameter Dict did not contain magnet_depth")
    else:
        magnet_depth = params["magnet_depth"]
        
    angle_total = 45 - mag_angle_deg
    h1 = params['outer_radius']/np.cos(np.deg2rad(angle_total/2))
    h2 = magnet_depth/np.cos(np.deg2rad(angle_total/2))
    h3 = h1 - h2
    g4 = h3*np.sin(np.deg2rad(angle_total/2))
    magnet_width = 2*g4
    inset = drawBurriedMagnet(magnet_width, magnet_depth, angle=45/2, group=11, material="N28UH", magdir=-180+angle_total/2)
    drawBurriedMagnet(magnet_width, magnet_depth, angle=45+45/2, group=12, material="N28UH", magdir=45+angle_total/2)
    drawLabel((params['outer_radius'] - inset/2)*np.cos(np.deg2rad(45/2)), (params['outer_radius'] - inset/2)*np.sin(np.deg2rad(45/2)), material="50JN400", group=5)
    drawLabel((params['outer_radius'] - inset/2)*np.cos(np.deg2rad(45+45/2)), (params['outer_radius'] - inset/2)*np.sin(np.deg2rad(45+45/2)), material="50JN400", group=5)
    drawLabel(params['outer_radius']/2, params['outer_radius']/2, material="50JN400", group=5)

    return {"magnet_width":magnet_width, "magnet_depth":magnet_depth}

if __name__ == "__main__":
    sys.exit(0)
