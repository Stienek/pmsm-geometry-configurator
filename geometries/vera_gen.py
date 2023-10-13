from femm import *
import sys, os
import numpy as np
import shutil

sys.path.insert(0, os.getcwd())
from modules.fem_util import *

mag_angle_deg = 0.5

def bdnry():
    return [[0.1, 3], [0.1, 50]]

def add_magnet(aa, ab, width, angle, direction, bdry="<None>", elemsize=0, automesh=1, posthide=0, group=0, material="<None>", meshsize=0, incircuit="<None>", magdir=0, turns=0, ro=16.1):
    angle = constrain(angle, -bdnry()[1][1], bdnry()[1][1])

    aa_rad = np.deg2rad(aa)
    ab_rad = np.deg2rad(ab)
    angle_rad = np.deg2rad(np.abs(angle) + (ab - aa)/2)
    ra = ro

    A = np.array([0, 0])
    b = ra
    a = width
    beta = np.pi - angle_rad

    s1 = a*np.sin(angle_rad)
    alpha = np.arcsin(s1/b)
    gamma = np.pi - alpha - beta
    c = np.sqrt(a**2 + b**2 - 2*a*b*np.cos(gamma))
    B = A + [c, 0]
    C = B + [a*np.cos(angle_rad), a*np.sin(angle_rad)]

    p1 = B
    p2 = C
    if np.abs(angle_rad) < ab_rad - aa_rad:
        a1 = ab_rad - aa_rad
        a2 = beta - np.pi/2
        a3 = np.pi - a1 - a2
        height = c*np.sin(a1)/np.sin(a3)
        r2 = np.sqrt(height**2 + c**2 - 2*height*c*np.cos(a2))
        p4 = np.array([r2*np.cos(ab_rad - aa_rad), r2*np.sin(ab_rad - aa_rad)])
        p3 = p2 + p4 - p1
    else:
        a1 = ab_rad - aa_rad - alpha
        a2 = np.pi/2 - gamma
        a3 = np.pi - a1 - a2
        height = b*np.sin(a1)/np.sin(a3)
        r2 = np.sqrt(height**2 + b**2 - 2*height*b*np.cos(a2))
        p3 = np.array([r2*np.cos(ab_rad - aa_rad), r2*np.sin(ab_rad - aa_rad)])
        p4 = p1 + p3 - p2

    center = p1 + (p3 - p1)/2
    if angle < 0:
        mirror = np.array([np.cos((ab_rad - aa_rad)/2), np.sin((ab_rad - aa_rad)/2)])
        mp = (np.dot(center, mirror) / np.dot(mirror, mirror)) * mirror
        center = 2 * mp - center

    rot = np.array([[np.cos(aa_rad), -np.sin(aa_rad)], [np.sin(aa_rad), np.cos(aa_rad)]])
    center = np.dot(rot, center)

    new_angle = angle + aa + (ab - aa)/2

    x1, x2, x3, x4 = drawRectangle(center[0], center[1], width, height, new_angle, magdir=convert_angle(new_angle - (180 if direction == -1 else 0)), bdry=bdry, elemsize=elemsize, automesh=automesh, posthide=posthide, group=group, material=material, meshsize=meshsize, incircuit=incircuit, turns=turns)
    return height, x1, x2, x3, x4

def create(params):
    if "magnet_depth" not in params:
        raise KeyError("Parameter Dict did not contain magnet_depth")
    else:
        magnet_width = params["magnet_depth"]
    if "magnet_angle" not in params:
        raise KeyError("Parameter Dict did not contain magnet_depth")
    else:
        angle = params["magnet_angle"]
    if "angle_margin" not in params:
        angle_margin = mag_angle_deg
    else:
        angle_margin = params["angle_margin"]

    ro = params['outer_radius']
    
    if magnet_width < bdnry()[0][0]:
        magnet_width = bdnry()[0][0]
    elif magnet_width > bdnry()[0][1]:
        magnet_width = bdnry()[0][1]

    hait, _, p1, p5, p6 = add_magnet(angle_margin/2, 90/4-angle_margin/2, magnet_width, angle, -1, material="N28UH", group=11, ro=ro)
    _, p9, _, p2, p12 = add_magnet(90/4+angle_margin/2, 2*90/4-angle_margin/2, magnet_width, -angle, -1, material="N28UH", group=12, ro=ro)
    _, _, p3, p10, p11 = add_magnet(2*90/4+angle_margin/2, 3*90/4-angle_margin/2, magnet_width, angle, 1, material="N28UH", group=13, ro=ro)
    _, p7, p8, p4, p34 = add_magnet(3*90/4+angle_margin/2, 4*90/4-angle_margin/2, magnet_width, -angle, 1, material="N28UH", group=14, ro=ro)

    drawLine(p1[0], p1[1], p2[0], p2[1])
    drawLine(p3[0], p3[1], p4[0], p4[1])

    c12 = (p1 + p2 + p12)/3
    c34 = (p3 + p4 + p34)/3
    c56 = (p5 + p6 + np.array([ro, 0]))/3
    c78 = (p7 + p8 + np.array([0, ro]))/3
    c911 = (p9 + p10 + p11)/3

    drawLabel(c12[0], c12[1], material="Air")
    drawLabel(c34[0], c34[1], material="Air")
    drawLabel(c56[0], c56[1], material="Air")
    drawLabel(c78[0], c78[1], material="Air")
    drawLabel(c911[0], c911[1], material="Air")

    drawLabel(np.cos(np.deg2rad(22.5))*(ro-0.1), np.sin(np.deg2rad(22.5))*(ro-0.1), material="50JN400")
    drawLabel(np.cos(np.deg2rad(22.5+45))*(ro-0.1), np.sin(np.deg2rad(22.5+45))*(ro-0.1), material="50JN400")

    drawLabel(np.cos(np.deg2rad(45))*((ro-params['inner_radius'])/2 + params['inner_radius']), np.sin(np.deg2rad(45))*((ro-params['inner_radius'])/2 + params['inner_radius']), material="50JN400")

    mi_clearselected()
    mi_selectsegment(0, ro-0.01)
    mi_selectsegment(ro-0.01, 0)
    mi_setsegmentprop('PeriodicRotor04', 1, 1, 0, 0) 
    mi_clearselected()
    return {"magnet_width":hait, 'x':magnet_width, 'y':angle}

if __name__ == "__main__":
    sys.exit(0) # Cleanly exit program.
