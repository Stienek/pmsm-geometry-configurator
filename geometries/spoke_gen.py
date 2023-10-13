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
    
    if "outer_radius"  in params:
        params['outer_radius'] = params["outer_radius"]
    else:
        params['outer_radius'] = 16.1

    magnet_width = magnet_depth
    magnet_inset = arcDepth(params['outer_radius'], magnet_width)
    magnet_inset_inside = arcDepth(params['inner_radius'], magnet_width)
    magnet_length = params['outer_radius'] - params['inner_radius'] + magnet_inset_inside

    drawLine(params['inner_radius'] - magnet_inset_inside, magnet_width/2, params['outer_radius'] - magnet_inset, magnet_width/2)
    drawLine(params['inner_radius'] - magnet_inset_inside, 0, params['inner_radius'] - magnet_inset_inside, magnet_width/2)
    drawLabel(params['outer_radius'] - magnet_width/2, magnet_width/4, material="N28UH", magdir=-90, group=11)
    
    drawLine(magnet_width/2, params['inner_radius'] - magnet_inset_inside, magnet_width/2, params['outer_radius'] - magnet_inset)
    drawLine(0, params['inner_radius'] - magnet_inset_inside, magnet_width/2, params['inner_radius'] - magnet_inset_inside)
    drawLabel(magnet_width/4, params['outer_radius'] - magnet_width/2, material="N28UH", magdir=0, group=12)

    
    drawLine(magnet_width/2, -(params['inner_radius'] - magnet_inset_inside), magnet_width/2, -(params['outer_radius'] - magnet_inset))
    drawLine(-magnet_width/2, -(params['inner_radius'] - magnet_inset_inside), -magnet_width/2, -(params['outer_radius'] - magnet_inset))
    drawLine(-magnet_width/2, -(params['inner_radius'] - magnet_inset_inside), magnet_width/2, -(params['inner_radius'] - magnet_inset_inside))
    
    mi_clearselected()
    mi_selectrectangle(-magnet_width/2, -(params['inner_radius'] - magnet_inset_inside), magnet_width/2, -(params['outer_radius'] - magnet_inset), 4) # Four means Select EVERYTHING
    mi_moverotate(0, 0, 135)
    drawLabel(np.cos(np.deg2rad(45))*((params['outer_radius']-params['inner_radius'])/2 + params['inner_radius']), np.sin(np.deg2rad(45))*((params['outer_radius']-params['inner_radius'])/2 + params['inner_radius']), material="N28UH", magdir=135, group=13)

    mi_clearselected()
    mi_selectarcsegment(np.cos(np.deg2rad(0))*(params['inner_radius']), np.sin(np.deg2rad(0))*(params['inner_radius']))
    mi_selectarcsegment(np.cos(np.deg2rad(45))*(params['inner_radius']), np.sin(np.deg2rad(45))*(params['inner_radius']))
    mi_selectarcsegment(np.cos(np.deg2rad(90))*(params['inner_radius']), np.sin(np.deg2rad(90))*(params['inner_radius']))
    mi_selectnode(0, params['inner_radius'])
    mi_selectnode(params['inner_radius'], 0)
    mi_deleteselected()
    drawLine(params['inner_radius'] - magnet_inset_inside, 0, params['outer_radius'], 0, bdry="PeriodicRotor02")
    drawLine(0, params['inner_radius'] - magnet_inset_inside, 0, params['outer_radius'], bdry="PeriodicRotor02")

    drawLabel(np.cos(np.deg2rad(45/2))*((params['outer_radius']-params['inner_radius'])/2 + params['inner_radius']), np.sin(np.deg2rad(45/2))*((params['outer_radius']-params['inner_radius'])/2 + params['inner_radius']), material="50JN400", group=5)
    drawLabel(np.cos(np.deg2rad(45/2 + 45))*((params['outer_radius']-params['inner_radius'])/2 + params['inner_radius']), np.sin(np.deg2rad(45/2+45))*((params['outer_radius']-params['inner_radius'])/2 + params['inner_radius']), material="50JN400", group=5)
    
    return {"magnet_width":magnet_length, "magnet_depth":magnet_width}

if __name__ == "__main__":
    sys.exit(0)
