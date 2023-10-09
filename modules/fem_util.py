from femm import *
from multimethod import overload 
import numpy as np

rotor_radius = 16.4 
outer_radius = 16.1 
inner_radius_bonus = 7.5 
inner_radius = 5.0 
magnet_area = 15.512 

def constrain(value, min_val, max_val):
    if isinstance(value, np.ndarray):
        return [min(max(v, min_val), max_val) for v in value]
    else:
        return min(max(value, min_val), max_val)

def convert_angle(angle):
    normalized_angle = angle % 360  
    if normalized_angle > 180:
        return normalized_angle - 360
    return normalized_angle

@overload
def arcDepth( x1, y1, x2, y2, angle):
    mid = np.array([(x1 + x2)/2, (y1 + y2)/2])
    linlength = np.sqrt((x1 - x2)**2 + (y1 - y2)**2)
    depth = linlength/2 * np.tan(np.deg2rad(angle)/4)
    vec = np.array([x2 - x1, y2 - y1])
    normvec = np.array([vec[1], -vec[0]])/linlength * depth
    midpoint = mid + normvec

    return (depth, midpoint)

@overload
def arcDepth(r, c):
    return r - np.sqrt(r**2 - c**2/4)

def arcAngle(r, c):
    return np.rad2deg(np.arctan(c/(r- arcDepth(r, c))))

def drawLine(x1, y1, x2, y2, bdry="<None>", elemsize=0, automesh=1, posthide=0, group=0):
    mid = np.array([(x1 + x2)/2, (y1 + y2)/2])
    mi_drawline(x1, y1, x2, y2)
    mi_clearselected() 
    mi_selectsegment(mid[0], mid[1]) 
    mi_setsegmentprop(bdry, elemsize, automesh, posthide, group) 
    mi_clearselected()
    return mid

def drawArc(x1, y1, x2, y2, angle, maxseg=1, bdry="<None>", posthide=0, group=0):
    if angle == 0:
        drawLine(x1, y1, x2, y2, bdry=bdry, group=group)
        return
    elif angle < 0:
        angle = np.abs(angle)
        x3 = x1 
        y3 = y1
        x1 = x2
        y1 = y2
        x2 = x3
        y2 = y3
    
    mi_drawarc(x1, y1, x2, y2, angle, maxseg)
    mi_clearselected()
    _, mid = arcDepth(x1, y1, x2, y2, angle)
    mi_selectarcsegment(mid[0], mid[1])
    mi_setarcsegmentprop(maxseg, bdry, posthide, group)
    mi_clearselected()
    return mid 

def drawLabel(x1, y1, material="<None>", automesh=1, meshsize=0, incircuit="<None>", magdir=0, group=0, turns=0):
    mi_addblocklabel(x1, y1)
    mi_clearselected()
    mi_selectlabel(x1, y1)
    mi_setblockprop(material, automesh, meshsize, incircuit, magdir, group, turns)
    mi_clearselected()
    return (x1, y1)

def drawRectangle(x, y, width, height, angle_degrees, bdry="<None>", elemsize=0, automesh=1, posthide=0, group=0, material="<None>", meshsize=0, incircuit="<None>", magdir=0, turns=0):
    angle_radians = np.deg2rad(angle_degrees)
    half_width = width / 2
    half_height = height / 2
    x1 = x + half_width * np.cos(angle_radians) - half_height * np.sin(angle_radians)
    y1 = y + half_width * np.sin(angle_radians) + half_height * np.cos(angle_radians)
    
    x2 = x - half_width * np.cos(angle_radians) - half_height * np.sin(angle_radians)
    y2 = y - half_width * np.sin(angle_radians) + half_height * np.cos(angle_radians)
    
    x3 = x - half_width * np.cos(angle_radians) + half_height * np.sin(angle_radians)
    y3 = y - half_width * np.sin(angle_radians) - half_height * np.cos(angle_radians)
    
    x4 = x + half_width * np.cos(angle_radians) + half_height * np.sin(angle_radians)
    y4 = y + half_width * np.sin(angle_radians) - half_height * np.cos(angle_radians)
    drawLine(x1, y1, x2, y2, bdry=bdry, elemsize=elemsize, automesh=automesh, posthide=posthide, group=group)
    drawLine(x2, y2, x3, y3, bdry=bdry, elemsize=elemsize, automesh=automesh, posthide=posthide, group=group)
    drawLine(x3, y3, x4, y4, bdry=bdry, elemsize=elemsize, automesh=automesh, posthide=posthide, group=group)
    drawLine(x4, y4, x1, y1, bdry=bdry, elemsize=elemsize, automesh=automesh, posthide=posthide, group=group)
    drawLabel(x, y, material=material, automesh=automesh, meshsize=meshsize, incircuit=incircuit, magdir=magdir, group=group, turns=turns)
    return np.array([x1, y1]), np.array([x2, y2]), np.array([x3, y3]), np.array([x4, y4])

def drawSurfaceMagnet(width, height, angle=-90, surface_radius=outer_radius, bdry="<None>", elemsize=0, automesh=1, posthide=0, group=0, material="<None>", meshsize=0, incircuit="<None>", magdir=0, turns=0):
    magnet_inset = arcDepth(surface_radius, width)
    drawLine(-width/2, -surface_radius + magnet_inset, -width/2, -surface_radius + height, bdry=bdry, elemsize=elemsize, automesh=automesh, posthide=posthide, group=group)
    drawLine(width/2, -surface_radius + magnet_inset, width/2, -surface_radius + height, bdry=bdry, elemsize=elemsize, automesh=automesh, posthide=posthide, group=group)
    drawLine(-width/2, -surface_radius + height, width/2, -surface_radius + height, bdry=bdry, elemsize=elemsize, automesh=automesh, posthide=posthide, group=group)
    mi_clearselected()
    mi_selectrectangle(-width/2, -surface_radius + magnet_inset, width/2, -surface_radius + height, 4)
    mi_moverotate(0, 0, 90 + angle)
    mi_clearselected()
    drawLabel((surface_radius - height/2)*np.cos(np.deg2rad(angle)), (surface_radius - height/2)*np.sin(np.deg2rad(angle)), material=material, automesh=automesh, meshsize=meshsize, incircuit=incircuit, magdir=magdir, group=group, turns=turns)

def drawBurriedMagnet(width, height, angle=-90, surface_radius=outer_radius, bdry="<None>", elemsize=0, automesh=1, posthide=0, group=0, material="<None>", meshsize=0, incircuit="<None>", magdir=0, turns=0):
    magnet_inset = arcDepth(surface_radius, width)
    drawLine(-width/2, -surface_radius + magnet_inset, -width/2, -surface_radius + height + magnet_inset, bdry=bdry, elemsize=elemsize, automesh=automesh, posthide=posthide, group=group)
    drawLine(width/2, -surface_radius + magnet_inset, width/2, -surface_radius + height + magnet_inset, bdry=bdry, elemsize=elemsize, automesh=automesh, posthide=posthide, group=group)
    drawLine(-width/2, -surface_radius + height + magnet_inset, width/2, -surface_radius + height + magnet_inset, bdry=bdry, elemsize=elemsize, automesh=automesh, posthide=posthide, group=group)
    drawLine(-width/2, -surface_radius + magnet_inset, width/2, -surface_radius + magnet_inset, bdry=bdry, elemsize=elemsize, automesh=automesh, posthide=posthide, group=group)
    mi_clearselected()
    mi_selectrectangle(-width/2, -surface_radius + magnet_inset, width/2, -surface_radius + height + magnet_inset, 4)
    mi_moverotate(0, 0, 90 + angle)
    mi_clearselected()
    drawLabel((surface_radius - height/2 - magnet_inset)*np.cos(np.deg2rad(angle)), (surface_radius - height/2 - magnet_inset)*np.sin(np.deg2rad(angle)), material=material, automesh=automesh, meshsize=meshsize, incircuit=incircuit, magdir=magdir, group=group, turns=turns)
    return magnet_inset
    
def drawTangentialMagnet(radius_inside, radius_outside, angle_inside_a, angle_inside_b, angle_outside_a, angle_outside_b, draw_first=True, draw_last=True, segments=1, bdry="<None>", elemsize=0, automesh=1, posthide=0, group=0, material="<None>", meshsize=0, incircuit="<None>", magdir=0, turns=0, maxseg=1):
    if segments <= 0:
        segments = 1
    for i in range(0, segments):
        arc_angle_inside = (angle_inside_b - angle_inside_a)/segments
        arc_angle_outside = (angle_outside_b - angle_outside_a)/segments
        p1_inside = np.array([radius_inside*np.cos(np.deg2rad(arc_angle_inside*i + angle_inside_a)), radius_inside*np.sin(np.deg2rad(arc_angle_inside*i + angle_inside_a))])
        p2_inside = np.array([radius_inside*np.cos(np.deg2rad(arc_angle_inside*(i + 1) + angle_inside_a)), radius_inside*np.sin(np.deg2rad(arc_angle_inside*(i + 1) + angle_inside_a))])
        p1_outside = np.array([radius_outside*np.cos(np.deg2rad(arc_angle_outside*i + angle_outside_a)), radius_outside*np.sin(np.deg2rad(arc_angle_outside*i + angle_outside_a))])
        p2_outside = np.array([radius_outside*np.cos(np.deg2rad(arc_angle_outside*(i + 1) + angle_outside_a)), radius_outside*np.sin(np.deg2rad(arc_angle_outside*(i + 1) + angle_outside_a))])
        drawArc(p1_inside[0], p1_inside[1], p2_inside[0], p2_inside[1], arc_angle_inside, maxseg=maxseg, bdry=bdry, posthide=posthide, group=group)
        if i == 0 and draw_first == True or i > 0:
            drawLine(p1_inside[0], p1_inside[1], p1_outside[0], p1_outside[1], bdry=bdry, elemsize=elemsize, automesh=automesh, posthide=1 if i > 0 else 0, group=group)
        if i == segments - 1 and draw_last == True:
            drawLine(p2_inside[0], p2_inside[1], p2_outside[0], p2_outside[1], bdry=bdry, elemsize=elemsize, automesh=automesh, posthide=posthide, group=group)
        label_angle = i*(arc_angle_inside + arc_angle_outside)/2 + (arc_angle_inside + arc_angle_outside)/4 + (angle_inside_a + angle_outside_a)/2
        drawLabel((p1_inside + (p2_outside - p1_inside)/2)[0], (p1_inside + (p2_outside - p1_inside)/2)[1], material=material, automesh=automesh, meshsize=meshsize, incircuit=incircuit, magdir=convert_angle(magdir + label_angle), group=group, turns=turns)
    return

def drawAbstactSurface(aa, ab, points, connect_ends=False):
    pnt = lambda r, phi: np.array([r*np.cos(np.deg2rad(phi)), r*np.sin(np.deg2rad(phi))])
    agl = np.linspace(aa, ab, len(points), endpoint=True)
    p1 = pnt(points[0], aa)
    if connect_ends:
        p1 = np.array(mi_selectnode(p1[0], p1[1]))
    for i in range(1, len(points)-1):
        p2 = pnt(points[i], agl[i])
        drawLine(p1[0], p1[1], p2[0], p2[1])
        p1 = p2
    p2 = pnt(points[-1], ab)
    if connect_ends:
        p2 = np.array(mi_selectnode(p2[0], p2[1]))
    drawLine(p1[0], p1[1], p2[0], p2[1])
    return