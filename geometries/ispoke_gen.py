from femm import *
import sys, os, shutil
import numpy as np

sys.path.insert(0, os.getcwd())
from modules.fem_util import *

mag_angle_deg = 6
outer_radius = 16.1

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

    if 'full' not in params:
        full = False
    else:
        full = params['full']
    
    points = np.loadtxt('tmp2.csv', delimiter=',')

    ro = np.min(points) - 0.15 if full else np.min(points)

    magnet_width = magnet_depth
    magnet_inset = arcDepth(ro, magnet_width)
    magnet_inset_inside = arcDepth(inner_radius, magnet_width)
    magnet_length = ro - inner_radius + magnet_inset_inside
    agl = arcAngle(outer_radius, magnet_width/2)
    mi_selectcircle(0, 0, 16.625, 4)
    mi_deleteselected()
    drawLine(0, 0, ro, 0)
    drawLine(0, 0, 0, ro)
    drawArc(ro, 0, 0, ro, 90)
    drawArc(inner_radius, 0, 0, inner_radius, 90)
    drawLine(ro, 0, 16.6, 0, bdry='PeriodicInAirGap01')
    drawLine(0, ro, 0, 16.6, bdry='PeriodicInAirGap01')
    drawArc(16.6, 0, 0, 16.6, 90, bdry='SlidingBand')
    
    drawLabel(1,1, material='Iron')
    drawLabel(16.55, 0.01, material='Air')
    mi_clearselected()
    mi_selectsegment(0.1, 0)
    mi_selectsegment(0, 0.1)
    mi_setsegmentprop('PeriodicRotor01', 1, 1, 0, 5) 
    pnt = lambda r, phi: np.array([r*np.cos(np.deg2rad(phi)), r*np.sin(np.deg2rad(phi))])
        
    drawLine(inner_radius - magnet_inset_inside, magnet_width/2, ro - magnet_inset, magnet_width/2)
    drawLine(inner_radius - magnet_inset_inside, 0, inner_radius - magnet_inset_inside, magnet_width/2)
    drawLabel(ro - magnet_width/2, magnet_width/4, material="N28UH", magdir=-90, group=11)
    
    drawLine(magnet_width/2, inner_radius - magnet_inset_inside, magnet_width/2, ro - magnet_inset)
    drawLine(0, inner_radius - magnet_inset_inside, magnet_width/2, inner_radius - magnet_inset_inside)
    drawLabel(magnet_width/4, ro - magnet_width/2, material="N28UH", magdir=0, group=12)

    drawLine(magnet_width/2, -(inner_radius - magnet_inset_inside), magnet_width/2, -(ro - magnet_inset))
    drawLine(-magnet_width/2, -(inner_radius - magnet_inset_inside), -magnet_width/2, -(ro - magnet_inset))
    drawLine(-magnet_width/2, -(inner_radius - magnet_inset_inside), magnet_width/2, -(inner_radius - magnet_inset_inside))
    mi_clearselected()
    mi_selectrectangle(-magnet_width/2, -(inner_radius - magnet_inset_inside), magnet_width/2, -(ro - magnet_inset), 4) # Four means Select EVERYTHING
    mi_moverotate(0, 0, 135)
    drawLabel(np.cos(np.deg2rad(45))*((ro-inner_radius)/2 + inner_radius), np.sin(np.deg2rad(45))*((ro-inner_radius)/2 + inner_radius), material="N28UH", magdir=135, group=13)

    mi_clearselected()
    mi_selectarcsegment(np.cos(np.deg2rad(0))*(inner_radius), np.sin(np.deg2rad(0))*(inner_radius))
    mi_selectarcsegment(np.cos(np.deg2rad(45))*(inner_radius), np.sin(np.deg2rad(45))*(inner_radius))
    mi_selectarcsegment(np.cos(np.deg2rad(90))*(inner_radius), np.sin(np.deg2rad(90))*(inner_radius))
    mi_selectnode(0, inner_radius)
    mi_selectnode(inner_radius, 0)
    mi_deleteselected()
    drawLine(inner_radius - magnet_inset_inside, 0, ro, 0, bdry="PeriodicRotor02")
    drawLine(0, inner_radius - magnet_inset_inside, 0, ro, bdry="PeriodicRotor02")

    drawLabel(np.cos(np.deg2rad(45/2))*((ro-inner_radius)/2 + inner_radius), np.sin(np.deg2rad(45/2))*((ro-inner_radius)/2 + inner_radius), material="50JN400", group=5)
    drawLabel(np.cos(np.deg2rad(45/2 + 45))*((ro-inner_radius)/2 + inner_radius), np.sin(np.deg2rad(45/2+45))*((ro-inner_radius)/2 + inner_radius), material="50JN400", group=5)
    p1 = pnt(ro, 22.5)
    p2 = pnt(ro, 67.5)
    mi_clearselected()
    mi_selectarcsegment(p1[0], p1[1])
    mi_selectarcsegment(p2[0], p2[1])
    mi_deleteselectedarcsegments()

    if full:
        drawAbstactSurface(0, 90, points)
    else:
        drawAbstactSurface(agl, 45-agl, points, connect_ends=True)
        drawAbstactSurface(45+agl, 90-agl, points, connect_ends=True)

    mi_selectsegment(ro-0.01, 0)
    mi_selectsegment(0, ro-0.01)
    mi_setsegmentprop('PeriodicRotor04', 1, 1, 0, 5)
    mi_clearselected()
    mi_selectsegment(ro+0.01, 0)
    mi_selectsegment(0, ro+0.01)
    mi_setsegmentprop('PeriodicRotor05', 1, 1, 0, 5)
    if full:
        mi_selectlabel(10, 4)
        mi_deleteselectedlabels()
        
    return {"magnet_width":magnet_length, "magnet_depth":magnet_width}

if __name__ == "__main__":
    openfemm()
    if os.path.exists("tmp.fem"):
        os.remove("tmp.fem")
    shutil.copyfile("stator_quater.FEM", "tmp.fem")
    opendocument("tmp.fem")
    points = np.loadtxt('tmp.csv', delimiter=',')
    create({'magnet_depth':2.5, 'full':True})
    input()
    closefemm()
    sys.exit(0) 
