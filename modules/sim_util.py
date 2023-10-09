from __future__ import print_function
import sys, os, shutil
import numpy as np
import time
from itertools import product
from concurrent import futures
from femm import *
import pandas as pd
import shutil
import matplotlib.pyplot as plt

sys.path.insert(0, os.getcwd())
import plt_util
from fem_util import *

def convert_seconds_to_formatted_string(seconds):
    weeks = seconds // (7 * 24 * 60 * 60)
    seconds %= 7 * 24 * 60 * 60
    
    days = seconds // (24 * 60 * 60)
    seconds %= 24 * 60 * 60
    
    hours = seconds // (60 * 60)
    seconds %= 60 * 60
    
    minutes = seconds // 60
    
    time_parts = []
    
    if weeks > 0:
        time_parts.append(f"{int(weeks)} week{'s' if weeks > 1 else ''}")
    
    if days > 0:
        time_parts.append(f"{int(days)} day{'s' if days > 1 else ''}")
    
    if hours > 0:
        time_parts.append(f"{int(hours)} hour{'s' if hours > 1 else ''}")
    
    time_parts.append(f"{int(minutes)} minute{'s' if minutes != 1 else ''}")
    
    formatted_string = ", ".join(time_parts)
    
    return formatted_string

def process_combo(func, combo):
    return func(*combo)

def simulate_general(params, func, filename, sims):
    try:
        simcombs = sims

        redict = params
        retarray = []
        openfemm(1)

        if not os.path.exists(filename):
            shutil.copyfile("stator_quater.FEM", filename)
        opendocument(filename)
        params.update(simcombs[0]) if len(simcombs) != 0 else 0
        retpars = func(params)
        redict.update(retpars)

        for simpar in simcombs:
            redict.update(simpar)
            mi_modifycircprop('A', 1, redict["irms"]*np.cos(np.deg2rad(redict["degel"])))
            mi_modifycircprop('B', 1, redict["irms"]*np.cos(np.deg2rad(redict["degel"]) + 2/3*np.pi))
            mi_modifycircprop('C', 1, redict["irms"]*np.cos(np.deg2rad(redict["degel"]) - 2/3*np.pi))
            
            mi_modifyboundprop("SlidingBand", 10, redict["degmech"])
            mi_analyse(1)
            mi_loadsolution()
            torque_airgap = mo_gapintegral("SlidingBand", 0)
            mo_clearblock()
            mo_groupselectblock(11)
            mo_groupselectblock(12)
            mo_groupselectblock(13)
            mo_groupselectblock(14)
            magarea = mo_blockintegral(5)
            circ_a = mo_getcircuitproperties('A')
            circ_b = mo_getcircuitproperties('B')
            circ_c = mo_getcircuitproperties('C')
            flux_a = circ_a[2]
            flux_b = circ_b[2]
            flux_c = circ_c[2]
            mo_close()

            redict.update({"magarea":magarea, "torque_airgap":torque_airgap, "flux_a":flux_a, "flux_b":flux_b, "flux_c":flux_c})
            retarray.append(dict(redict))

        closefemm()
        
        return retarray
    except Exception as e:
        try:
            closefemm()
        except Exception:
            pass
        print(e)
        return None

def multiSimHandler(simfunc, simpath, rotfunc, steps, sims, rettype='df'):
    with futures.ProcessPoolExecutor(12) as executor:
        print("---------------------------------------------")
        print(f"Starting Simulation {simpath}.")
        time_start = time.time()

        if not os.path.exists(simpath):
            os.makedirs(simpath)
        else:
            shutil.rmtree(simpath)
            os.makedirs(simpath)

        combos = createCombos(steps)

        tasks = [executor.submit(process_combo, simfunc, [combo, rotfunc, os.path.join(simpath, '_'.join([f'{key}_{value}' for key, value in combo.items()]) + ".FEM"), createCombos(sims)]) for combo in combos]
        if rettype == 'df':
            results = []
        else:
            results = [{} for _ in range(len(combos))]
        index = 0
        max_index = len(combos)
        for future in futures.as_completed(tasks):
            res = future.result()
            index += 1
            if res is not None:
                if rettype == 'df':
                    [results.append(redict) for redict in res]
                else:
                    results[res[0]['kk']-1].update(res[0])
                print(f"Ran step {index}/{max_index} ({100*index/max_index:.2f}%). Time remaining: {convert_seconds_to_formatted_string((time.time()-time_start)*(max_index-index)/(index if index > 0 else 1))}")
            else:
                print(f"Dropped step {index}/{max_index}.")

        if rettype == 'df':
            ret = pd.DataFrame(results)
        else:
            ret = results

        time_end = time.time()
        print(f"Finished Simulation {simpath}.")
        print(f'Total time ellapsed: {convert_seconds_to_formatted_string(time_end-time_start)}')

    return ret
def createCombos(parameters):
    def recurse(item):
        if isinstance(item, list) and len(item) == 3 and all(isinstance(element, (int, float)) for element in item):
            return np.linspace(*item)
        elif isinstance(item, tuple):
            return list(item)
        elif isinstance(item, list):
            res = []
            for sublist in item:
                [res.append(val) for val in recurse(sublist)]
            return res
        elif isinstance(item, dict):
            if "parameters" not in item or "func" not in item:
                raise KeyError("Function Parameters need both paremeters and func")
            if "mode" not in item:
                mode = 'select'
            else:
                mode = item["mode"]
            res = []
            combs = createCombos(item["parameters"])
            if mode == "select":
                [res.append(x) for x in combs if item["func"](x)]
            elif mode == "create":
                [res.append(item["func"](x)) for x in combs if item['func'](x) != None]
            else:
                raise KeyError("Wrong function mode selected.")
            return res
        else:
            return [item]
        
    def flatten_dict(dick):
        if isinstance(dick, list):
            return [flatten_dict(dig) for dig in dick]
        result = {}
        for key, value in dick.items():
            if isinstance(value, dict):
                nested_result = flatten_dict(value)
                result.update(nested_result)
            else:
                result[key] = value
        return result

    keys = list(parameters.keys())
    values = [recurse(param_range) for param_range in parameters.values()]
    combinations = list(product(*values))
    result = [dict(zip(keys, combination)) for combination in combinations]
    return flatten_dict(result)

def simulate_ld_lq(rotor, params):
    openfemm(1)
    if os.path.exists("tmp.fem"):
        os.remove("tmp.fem")
    shutil.copyfile("stator_quater.FEM", "tmp.fem")
    opendocument("tmp.fem")
    rotor.create(params)
    mi_modifymaterial('N28UH', 3, 0)
    mi_modifyboundprop("SlidingBand", 10, 22.5)
    if 'i' not in params:
        params.update({'i':12})
    tta = 0
    Id = params['i']*np.array([np.cos(tta), np.cos(tta-2*np.pi/3), np.cos(tta+2*np.pi/3)])
    Iq = params['i']*np.array([-np.sin(tta), -np.sin(tta-2*np.pi/3), -np.sin(tta+2*np.pi/3)])
    
    mi_setcurrent('A', Id[0])
    mi_setcurrent('C', Id[1])
    mi_setcurrent('B', Id[2])
    
    mi_smartmesh(0)
    mi_analyze(1)
    mi_loadsolution()
    mo_smooth('on')

    psiad = mo_getcircuitproperties('A')[2]
    psibd = mo_getcircuitproperties('B')[2]
    psicd = mo_getcircuitproperties('C')[2]

    mo_close()

    mi_setcurrent('A', Iq[0])
    mi_setcurrent('C', Iq[1])
    mi_setcurrent('B', Iq[2])

    mi_smartmesh(0)
    mi_analyze(1)
    mi_loadsolution()
    mo_smooth('on')
    
    psibq = mo_getcircuitproperties('B')[2]
    psicq = mo_getcircuitproperties('C')[2]

    closefemm()

    ld = 4*2/3*(psiad - 1/2*psibd - 1/2*psicd)
    lq = 4/np.sqrt(3)*(psicq - psibq)
    
    return {'ld':3/4*1e6*ld/params['i'], 'lq':3/4*1e6*lq/params['i']}

def simulate_airgap_harmonics(rotor, params):
    openfemm(1)
    if os.path.exists("tmp.fem"):
        os.remove("tmp.fem")
    shutil.copyfile("stator_quater.FEM", "tmp.fem")
    opendocument("tmp.fem")
    rotor.create(params)
    mi_modifyboundprop("SlidingBand", 10, 0)
    if 'i' not in params:
        params.update({'i':0})
    tta = 0
    Id = params['i']*np.array([np.cos(tta), np.cos(tta-2*np.pi/3), np.cos(tta+2*np.pi/3)])
    Iq = params['i']*np.array([-np.sin(tta), -np.sin(tta-2*np.pi/3), -np.sin(tta+2*np.pi/3)])
    
    mi_setcurrent('A', Id[0])
    mi_setcurrent('C', Id[1])
    mi_setcurrent('B', Id[2])
    
    mi_smartmesh(0)
    mi_analyze(1)
    mi_loadsolution()
    mo_smooth('on')

    nh = mo_getgapharmonics('SlidingBand')

    h = []
    print(nh)
    for i in range(4, 7*4 + 1, 4):
        hi = mo_getgapharmonics('SlidingBand', i)
        h.append(np.sqrt(hi[2]**2 + hi[3]**2))

    closefemm()
    print(h)
    
    return {'ha1': h[0], 'ha2': h[1], 'ha3': h[2], 'ha4': h[3], 'ha5': h[4], 'ha6': h[5], 'ha7': h[6]}

def simulate_everything(rotor, params, simname):
    if not os.path.exists(os.path.join('results', simname)):
        os.makedirs(os.path.join('results', simname))
    df = {'name':simname}
    # df.update(simulate_ld_lq(rotor, params))
    # df.update(simulate_constants(rotor, params, simname))
    df.update(simulate_torque_and_backemf(rotor, params, simname))
    df.update(simulate_torque_moving(rotor, params, simname))
    # df.update(simulate_airgap_harmonics(rotor, params))
    return df



def simulate_constants(rotor, params, simname):
    simpath = os.path.join('results', 'sims', simname + '_steps')
    steps = {
        'degmech': [35, 55, 40]
    }
    sims = {
        "irms": np.sqrt(2)*12,
        'degel': 0
    }
    sims.update(params)
    data = multiSimHandler(simulate_general, simpath, rotor.create, steps, sims)
    df = pd.DataFrame(data)
    df.plot()
    plt.show()
    print(df['torque_airgap'].max())
    kt = np.sqrt(2)*df['torque_airgap'].max()/sims['irms']
    km = 2*df['torque_airgap'].max()/np.sqrt(sims['irms']**2*0.273/2)
    return {'k_torque':kt, 'k_motor':km}

def simulate_torque_and_backemf(rotor, params, simname):
    simpath = os.path.join('results','sims', simname, simname + '_steps')
    csvpath = os.path.join("results", simname, simname + '_tbemf.csv')
    respath = os.path.join(plt_util.texpath, simname)
    if not os.path.exists(respath):
        os.makedirs(respath)
    respath = os.path.join(respath, simname + '_tbemf')
    if not os.path.exists(csvpath):
        steps = {
            'degmech': [0, 90, 90*5]
        }
        sims = {
            "irms": 0,
            'degel': 0
        }
        sims.update(params)
        data = multiSimHandler(simulate_general, simpath, rotor.create, steps, sims)
        data.to_csv(csvpath, header=True, index=False)

    df = pd.read_csv(csvpath)
    df1 = df[df['irms'] == 0]
    df1.sort_values(by='degmech', inplace=True)
    df1.reset_index(drop=True, inplace=True)

    amin = min(df1['degmech'])
    amax = max(df1['degmech'])
    rotational_speed_rpm = 3000  
    ns = rotational_speed_rpm/60
    T = 1/ns
    num_data_points = len(df1)

    dt = (amax-amin)/360*T/num_data_points

    tt = np.arange(0, num_data_points) * dt

    torque = df1['torque_airgap'].values
    aflux = df1['flux_a'].values
    cflux = df1['flux_c'].values
    
    va = 4 * np.diff(aflux)/dt
    vc = 4 * np.diff(cflux)/dt
    
    td = tt[:-1] + dt / 2
    
    vll = va - vc
    tt = tt*1000
    td = td*1000

    fig, ax = plt_util.twinPlot({
    "1":{
        'x': tt, 
        'y': torque, 
        'label':r'$M_{Rel}$'
        }, 
    "3":{
        'x': td, 
        'y': va, 
        'label':r'Einphasige induzierte Spannung'
        },
    "4":{
        'x': td, 
        'y': vll, 
        'label':r'Phase-Phase Spannung'
        },
    'y1label':r'Drehmoment in Nm',
    'y2label':r'Spannung in V',
    'x1label':r'Zeit in ms',
    }, fraction=0.6, ratio=2, labelloc='lower center')
    fig.savefig(respath + '.pdf', bbox_inches='tight')
    plt.close(fig)
    return {'k_emf':max(vll)/(2*np.pi*ns)}

def simulate_torque_moving(rotor, params, simname):
    simpath = os.path.join('results','sims', simname, simname + '_steps')
    csvpath = os.path.join("results", simname, simname + '_mov.csv')
    respath = os.path.join(plt_util.texpath, simname)
    if not os.path.exists(respath):
        os.makedirs(respath)
    respath = os.path.join(respath, simname + '_mov')
    if not os.path.exists(csvpath):
        steps = {
            'pos':{
                'parameters': {'deg':[0, 90, 90*5]},
                'func': lambda x: {'degel':4*x['deg'], 'degmech':x['deg']+45},
                'mode':'create'
            },
        }
        sims = {
            "irms": np.sqrt(2)*12,
        }
        sims.update(params)
        data = multiSimHandler(simulate_general, simpath, rotor.create, steps, sims)
        data.to_csv(csvpath, header=True, index=False)

    df = pd.read_csv(csvpath)
    df1 = df[df['irms'] == np.sqrt(2)*12]
    df1.sort_values(by='degmech', inplace=True)
    df1.reset_index(drop=True, inplace=True)

    amin = min(df1['degmech'])
    amax = max(df1['degmech'])
    rotational_speed_rpm = 3000  
    ns = rotational_speed_rpm/60
    T = 1/ns
    num_data_points = len(df1)

    dt = (amax-amin)/360*T/num_data_points

    tt = np.arange(0, num_data_points) * dt

    torque = df1['torque_airgap'].values
    aflux = df1['flux_a'].values
    cflux = df1['flux_c'].values
    
    va = 4 * np.diff(aflux)/dt
    vc = 4 * np.diff(cflux)/dt
    
    td = tt[:-1] + dt / 2
    
    vll = va - vc
    tt = tt*1000
    td = td*1000

    fig, ax = plt_util.twinPlot({
    "1":{
        'x': tt, 
        'y': torque, 
        'label':r'$M$'
        }, 
    "3":{
        'x': td, 
        'y': -va, 
        'label':r'Einphasige induzierte Spannung'
        },
    "4":{
        'x': td, 
        'y': -vll, 
        'label':r'Phase-Phase Spannung'
        },
    'y1label':r'Drehmoment in Nm',
    'y2label':r'Spannung in V',
    'x1label':r'Zeit in ms',
    }, fraction=0.6, ratio=2, labelloc='lower center')
    fig.savefig(respath + '.pdf', bbox_inches='tight')
    plt.close(fig)
    Mavg = torque.mean()
    Mac = np.sqrt(sum([(x - Mavg)**2 for x in torque])/len(torque))
    fftv = np.abs(np.fft.fft(torque))
    pin = np.sqrt(3)*12*24
    pout = 2*np.pi*ns*Mavg
    theta = pout/pin
    return {'torque_dc':Mavg, 'torque_ac':Mac, 'theta':theta}

def sweep_1d(rotor, simname,labelloc='upper left'):
    simpath = os.path.join('results','sims', simname, simname + '_steps')
    csvpath1 = os.path.join("results", simname, simname + '_sweep_stand.csv')
    csvpath2 = os.path.join("results", simname, simname + '_sweep_movin.csv')
    respath = os.path.join(plt_util.texpath, simname)
    if not os.path.exists(respath):
        os.makedirs(respath)
    respath = os.path.join(respath, simname)
    irms = np.sqrt(2)*12
    if not os.path.exists(csvpath1):
        steps1 = {
            "magnet_depth":[rotor.bdnry()[0], rotor.bdnry()[1], 48],
        }
        sims1 = {
            "irms":(0, irms),
            "degel":0,
            "degmech":[0, 90, 46],
        }
        data1 = multiSimHandler(simulate_general, simpath, rotor.create, steps1, sims1)
        data1.to_csv(csvpath1, header=True, index=False)
    if not os.path.exists(csvpath2):
        steps2 = {
            "magnet_depth":[rotor.bdnry()[0], rotor.bdnry()[1], 48],
        }
        sims2 = {
            "irms":irms,
            'pos':{
                'parameters': {'deg':[0, 90, 46]},
                'func': lambda x: {'degel':4*x['deg'], 'degmech':x['deg']+45},
                'mode':'create'
            },
        }
        data2 = multiSimHandler(simulate_general, simpath, rotor.create, steps2, sims2)
        data2.to_csv(csvpath2, header=True, index=False)

    df1 = pd.read_csv(csvpath1)

    filtered_data_on = df1[df1['irms'] == irms]

    pivot_table_on = filtered_data_on.pivot_table(
        values='torque_airgap', 
        index='magnet_depth',     
        columns='degmech',        
        aggfunc='first'       
    )

    sorted_pivot_table_on = pivot_table_on.sort_index(ascending=True).sort_index(axis=1, ascending=True)

    fig1, _ = plt_util.create_heatmap_interp(sorted_pivot_table_on, xlabel=r"Mechanische Position in Grad", ylabel=r"Magnetdicke in mm", zlabel=r"Drehmoment in Nm", clevels=10, fraction=0.6)
    fig1.savefig(respath + "_on.pdf", bbox_inches='tight')
    plt.close(fig1)
    
    filtered_data_off = df1[df1['irms'] == 0]

    pivot_table_off = filtered_data_off.pivot_table(
        values='torque_airgap',  
        index='magnet_depth',  
        columns='degmech',       
        aggfunc='first'        
    )

    sorted_pivot_table_off = pivot_table_off.sort_index(ascending=True).sort_index(axis=1, ascending=True)

    fig2, _ = plt_util.create_heatmap_interp(sorted_pivot_table_off, xlabel=r"Mechanische Position in Grad", ylabel=r"Magnetdicke in mm", zlabel=r"Drehmoment in Nm", clevels=4, fraction=0.6)
    fig2.savefig(respath + "_off.pdf", bbox_inches='tight')
    plt.close(fig2)

    df2 = pd.read_csv(csvpath2)

    filtered_data_rot = df2[df2['irms'] == irms]

    pivot_table_rot = filtered_data_rot.pivot_table(
        values='torque_airgap', 
        index='magnet_depth',   
        columns='degmech',      
        aggfunc='first'         
    )

    sorted_pivot_table_rot = pivot_table_rot.sort_index(ascending=True).sort_index(axis=1, ascending=True)

    fig3, _ = plt_util.create_heatmap_interp(sorted_pivot_table_rot, xlabel=r"Mechanische Position in Grad", ylabel=r"Magnetdicke in mm", zlabel=r"Drehmoment in Nm", clevels=6, fraction=0.7)
    fig3.savefig(respath + "_rot.pdf", bbox_inches='tight')
    plt.close(fig3)
    
    max_torque_rows = df1.loc[df1.groupby(['magnet_depth', 'irms'])['torque_airgap'].idxmax()]

    on = max_torque_rows[max_torque_rows['irms'] == irms].sort_values(by='magnet_depth', ascending=True)
    off = max_torque_rows[max_torque_rows['irms'] == 0].sort_values(by='magnet_depth', ascending=True)

    grouped = df2.groupby('magnet_depth')['torque_airgap'].agg(['mean', lambda x: np.sqrt(((x - x.mean())**2).sum() / len(x))]).reset_index()
    grouped.columns = ['magnet_depth', 'mean', 'ripple']
    combined1 = []
    for i in range(len(off)):
        combined1.append(off.iloc[i]['torque_airgap']/ on.iloc[i]['torque_airgap'])
    combined2 = grouped['ripple']/grouped['mean']
    fig4, _ = plt_util.twinPlot({
        "1":{
            'x': on['magnet_depth'], 
            'y': on['torque_airgap'], 
            'label':r'$M_{Kipp}$'
            }, 
        '2':{
            'x': off['magnet_depth'], 
            'y': off['torque_airgap'], 
            'label':r'$M_{Reluktanz,max}$'
            }, 
        '3':{
            'x': on['magnet_depth'], 
            'y': combined1[:], 
            'label':r'$\frac{M_{Reluktanz,max}}{M_{Kipp}}$'
            },
        'y1label':r'Drehmoment in Nm',
        'y2label':r'Drehmomentwelligkeit',
        'x1label':r'Magnetdicke in mm',
        }, fraction=0.6, labelloc=labelloc)
    fig4.savefig(respath + "_1da.pdf", bbox_inches='tight')
    plt.close(fig4)
    fig5, _ = plt_util.twinPlot({
        "1":{
            'x': grouped['magnet_depth'], 
            'y': grouped['mean'], 
            'label':r'$M_{-}$'
            }, 
        '2':{
            'x': grouped['magnet_depth'], 
            'y': grouped['ripple'], 
            'label':r'$M_{\sim}$'
            }, 
        '3':{
            'x': grouped['magnet_depth'], 
            'y': combined2, 
            'label':r'$\frac{M_{\sim}}{M_{-}}$'
            }, 
        'y1label':r'Drehmoment in Nm',
        'y2label':r'Drehmomentwelligkeit',
        'x1label':r'Magnetdicke in mm',
        }, fraction=0.6, labelloc=labelloc)

    fig5.savefig(respath + "_1db.pdf", bbox_inches='tight')
    plt.close(fig5)
    return

def sweep_2d(rotor, simname, steps, ylabel, xlabel=r"Magnetdicke in mm"):
    simpath = os.path.join('results','sims', simname, simname + '_steps')
    csvpath1 = os.path.join("results", simname, simname + '_sweep_stand.csv')
    csvpath2 = os.path.join("results", simname, simname + '_sweep_movin.csv')
    respath = os.path.join(plt_util.texpath, simname)
    if not os.path.exists(respath):
        os.makedirs(respath)
    respath = os.path.join(respath, simname)
    irms = np.sqrt(2)*12
    if not os.path.exists(csvpath1):
        sims = {
            "irms":(0, irms),
            "degel":0,
            "degmech":[22.5, 67.5, 11],
        }
        data = multiSimHandler(simulate_general, simpath, rotor.create, steps, sims)
        data.to_csv(csvpath1, header=True, index=False)
    
    if not os.path.exists(csvpath2):
        sims = {
            "irms":irms,
            'pos':{
                'parameters': {'deg':[22.5, 67.5, 11]},
                'func': lambda x: {'degel':4*x['deg'], 'degmech':x['deg']},
                'mode':'create'
            },
        }
        data = multiSimHandler(simulate_general, simpath, rotor.create, steps, sims)
        data.to_csv(csvpath2, header=True, index=False)

    df1 = pd.read_csv(csvpath1)
    df1.dropna()

    filtered_data_on = df1[df1['irms'] == irms]

    pivot_table_on = filtered_data_on.pivot_table(
        values='torque_airgap', 
        index='x',     
        columns='y',        
        aggfunc='max'         
    )

    sorted_pivot_table_on = pivot_table_on.sort_index(ascending=True).sort_index(axis=1, ascending=True).fillna(0)
    
    fig1, _ = plt_util.create_heatmap_interp(sorted_pivot_table_on, ylabel=xlabel, xlabel=ylabel, zlabel=r"Drehmoment in Nm", fraction=0.6)
    fig1.savefig(respath + "_on.pdf", bbox_inches='tight')
    plt.close(fig1)
    
    filtered_data_off = df1[df1['irms'] == 0]

    pivot_table_off = filtered_data_off.pivot_table(
        values='torque_airgap', 
        index='x',     
        columns='y',        
        aggfunc='max'          
    )
    sorted_pivot_table_off = pivot_table_off.sort_index(ascending=True).sort_index(axis=1, ascending=True).fillna(0)
    
    fig2, _ = plt_util.create_heatmap_interp(sorted_pivot_table_off, ylabel=xlabel, xlabel=ylabel, zlabel=r"Drehmoment in Nm", fraction=0.6)
    fig2.savefig(respath + "_off.pdf", bbox_inches='tight')
    plt.close(fig2)
    
    df2 = pd.read_csv(csvpath2)
    df2.dropna()

    filtered_data_rot = df2[df2['irms'] == irms]
    grouped = filtered_data_rot.groupby(['x', 'y'])['torque_airgap'].agg(['mean', lambda x: np.sqrt(((x - x.mean())**2).sum() / len(x))]).reset_index()
    grouped.columns = ['x', 'y', 'mean', 'ripple']
    
    pivot_table_rot = grouped.pivot_table(
        values='mean',  
        index='x',     
        columns='y',        
        aggfunc='first'       
    )

    sorted_pivot_table_rot = pivot_table_rot.sort_index(ascending=True).sort_index(axis=1, ascending=True).fillna(0).abs()

    fig3, _ = plt_util.create_heatmap_interp(sorted_pivot_table_rot, ylabel=xlabel, xlabel=ylabel, zlabel=r"Drehmoment in Nm", fraction=0.6)
    fig3.savefig(respath + "_rot_dc.pdf", bbox_inches='tight')
    plt.close(fig3)
    
    pivot_table_ac = grouped.pivot_table(
        values='ripple',  
        index='x',     
        columns='y',        
        aggfunc='first'        
    )

    sorted_pivot_table_ac = pivot_table_ac.sort_index(ascending=True).sort_index(axis=1, ascending=True).fillna(0)

    fig4, _ = plt_util.create_heatmap_interp(sorted_pivot_table_ac, ylabel=xlabel, xlabel=ylabel, zlabel=r"Drehmoment in Nm", fraction=0.6)

    fig4.savefig(respath + "_rot_ac.pdf", bbox_inches='tight')
    plt.close(fig4)
    tabl1 = (sorted_pivot_table_on/sorted_pivot_table_off).fillna(0)
    table1 = tabl1.applymap(lambda x: constrain(x, 0, 10))
    fig5, _ = plt_util.create_heatmap_interp(table1, ylabel=xlabel, xlabel=ylabel, zlabel=r"$\frac{M_{Kipp}}{M_{rel,max}}$", fraction=0.7)
    
    fig5.savefig(respath + "_ratio.pdf", bbox_inches='tight')
    plt.close(fig5)
    tabl2 = (sorted_pivot_table_ac/sorted_pivot_table_rot).fillna(0)
    table2 = tabl2.applymap(lambda x: constrain(x, 0, 1))
    fig6, _ = plt_util.create_heatmap_interp(table2, ylabel=xlabel, xlabel=ylabel, zlabel=r"Drehmomentwelligkeit", fraction=0.7)
    fig6.savefig(respath + "_wellig.pdf", bbox_inches='tight')
    plt.close(fig6)
    return

def simulate_loss_step(params, func, filename, sims):
    try:      
        simcombs = sims
        if len(simcombs) != 0:
            params.update(simcombs[0])

        k = (params['kk']-1)*params['dk'] 

        redict = params
        retarray = []
        
        openfemm(1)

        if not os.path.exists(filename):
            shutil.copyfile("stator_quater.FEM", filename)
        opendocument(filename)
        retpars = func(params)
        redict.update(retpars)

        for simpar in simcombs:
            redict.update(simpar)
            mi_modifyboundprop("SlidingBand", 10, k+22.5)
            tta = np.deg2rad(params['RotorMagnets']/2*k)
            Id = np.array([np.cos(tta), np.cos(tta-2*np.pi/3), np.cos(tta+2*np.pi/3)])
            Iq = np.array([-np.sin(tta), -np.sin(tta-2*np.pi/3), -np.sin(tta+2*np.pi/3)])
            Itot =  params['MyIdCurrent']*Id + params['MyIqCurrent']*Iq
            mi_setcurrent('A', Itot[0])
            mi_setcurrent('C', Itot[1])
            mi_setcurrent('B', Itot[2])
            
            mi_smartmesh(0)
            mi_analyze(1)
            mi_loadsolution()
            mo_smooth('on')
            
            nn = mo_numelements()
            A = np.zeros((nn, 1))
            b = np.zeros((nn, 1),dtype=complex)
            for m in range(nn):
                if params['g'][m] > 10:
                    A[m] = mo_geta(np.real(params['z'][m])[0],np.imag(params['z'][m])[0])
                elif params['g'][m] > 0:
                    btmp = mo_getb(np.real(params['z'][m])[0], np.imag(params['z'][m])[0])	
                    b[m] =  btmp[0]*1 + btmp[1]*1j
                continue

            tq = mo_gapintegral('SlidingBand',0)
            mo_close()

            redict.update({'k':k,'tq':tq, 'A':A.flatten(), 'b':b.flatten()})
            retarray.append(dict(redict))

        closefemm()
        return retarray
    except Exception as e:
        try:
            closefemm()
        except Exception:
            pass
        print(e)
        return None
    
def donothing(params):
    return params

def simulate_point_data(params, func, filename, sims):
    try:      
        simcombs = sims
        if len(simcombs) != 0:
            params.update(simcombs[0])

        redict = params
        retarray = []
        
        openfemm(1)

        if not os.path.exists(filename):
            shutil.copyfile("stator_quater.FEM", filename)
            
        opendocument(filename)
        
        retpars = func(params)
        redict.update(retpars)

        for simpar in simcombs:
            redict.update(simpar)
            k = 0
            mi_modifyboundprop("SlidingBand", 10, k + 22.5)
             
            tta = np.deg2rad(params['RotorMagnets']/2*k)
            Id = np.array([np.cos(tta), np.cos(tta-2*np.pi/3), np.cos(tta+2*np.pi/3)])
            Iq = np.array([-np.sin(tta), -np.sin(tta-2*np.pi/3), -np.sin(tta+2*np.pi/3)])
            Itot =  params['MyIdCurrent']*Id + params['MyIqCurrent']*Iq
            mi_setcurrent('A', Itot[0])
            mi_setcurrent('C', Itot[1])
            mi_setcurrent('B', Itot[2])
            mi_smartmesh(0)

            mi_analyze(1)
            mi_loadsolution()
            mo_smooth('on')
            
            nn = mo_numelements()
            z = np.zeros((nn,1),dtype=complex) 
            a = np.zeros((nn,1)) 
            g = np.zeros((nn,1)) 
            triag = np.zeros((nn, 3, 2))
            for m in range(nn):
                elm = mo_getelement(m+1)
                
                p1 = mo_getnode(elm[0])
                p2 = mo_getnode(elm[1])
                p3 = mo_getnode(elm[2])
                triag[m, :, :] = np.array([[p1[0], p1[1]], [p2[0], p2[1]], [p3[0], p3[1]]])


                z[m] = elm[3] + 1j*elm[4]
                a[m] = elm[5]
                g[m] = elm[6]
            probinfo = mo_getprobleminfo()

            redict.update({'z':z.flatten(), 'a':a.flatten(), 'g':g.flatten(), 'nn':nn, 'probinfo':probinfo, 'triag':triag})
            retarray.append(dict(redict))

        closefemm()
        return retarray
    except Exception as e:
        try:
            closefemm()
        except Exception:
            pass
        print(e)
        return None
    
def simulate_losses(rotor, params, simname):
    simpath = os.path.join('results', simname, simname + '_steps')
    datpath = os.path.join("results", simname, simname + '_heatdata.csv')
    respath = os.path.join("results", simname, simname + '_losses')

    symetry_factor = 4

    wbase=3000/60 

    SpeedMin = 100
    SpeedMax = 3000
    SpeedStep = 10 

    MyIdCurrent = 0 
    MyIqCurrent = 12*np.sqrt(2) 
    MyLowestHarmonic = 2 
    AWG=0.00063	
    WindingFill=1
    PhaseResistance = 0.273/2 
    TemperatureRise = 60 

    RotorMagnets = 8
    omag = 0.556*10**6

    ce = 0.887776453191364 
    ch = 385.326942698947 
    cs = 0.95  

    Pi=np.pi

    n = 360/MyLowestHarmonic

    dk = 0.5

    dwire=AWG 
    owire = (58*10**6)/(1+TemperatureRise*0.004) 
    cePhase = (Pi**2/8)*dwire**2*WindingFill*owire

    def save_data(filename, *arrays):
        np.savez(filename, *arrays)

    def load_data(filename):
        data = np.load(filename)
        return tuple(data[k] for k in data.files)
    
    runsim = False if os.path.exists(simpath + '.npz') else True 
    if runsim:
        points = multiSimHandler(simulate_point_data, simpath, rotor, params, {'kk':1, 'dk':dk, 'RotorMagnets':RotorMagnets, 'MyIdCurrent':MyIdCurrent, 'MyIqCurrent':MyIqCurrent}, rettype='array')
        nn = points[0]['nn']
        probinfo = points[0]['probinfo']

        b = np.zeros((int(np.floor(n/dk)),nn), dtype=complex) 
        A = np.zeros((int(np.floor(n/dk)),nn)) 
        z = np.zeros((nn,1), dtype=complex) 
        a = np.zeros((nn,1))
        g = np.zeros((nn,1)) 
        tq = np.zeros((int(np.floor(n/dk)),1))
        triag = np.zeros((nn, 3, 2))

        z[:, 0] = points[0]['z']
        a[:, 0] = points[0]['a']
        g[:, 0] = points[0]['g']
        triag = points[0]['triag']
        
        steppar = {
            'kk':tuple(range(1, int(np.floor(n/dk))+1)),
        }
        steppar.update(params)
        data = multiSimHandler(simulate_loss_step, simpath, rotor, steppar, {'dk':dk, 'RotorMagnets':RotorMagnets, 'MyIdCurrent':MyIdCurrent, 'MyIqCurrent':MyIqCurrent, 'z':z, 'g':g}, rettype='array')
        
        for idx in range(len(data)):
            A[idx, :] = data[idx]['A']
            b[idx, :] = data[idx]['b']
            tq[idx, 0] = data[idx]['tq']
        
        save_data(simpath + '.npz', nn, probinfo, b, A, z, a, g, tq, triag)
    else:
        loaded_data = load_data(simpath + '.npz')
        nn, probinfo, b, A, z, a, g, tq, triag = loaded_data
    ns = n / dk
    bxfft = np.abs(np.fft.fft(np.real(b), axis=0)) * (2 / ns)
    byfft = np.abs(np.fft.fft(np.imag(b), axis=0)) * (2 / ns)
    bsq = (bxfft * bxfft) + (byfft * byfft)

    h = probinfo[2] 
    lengthunits = probinfo[3] 
    v = a * h * lengthunits**2

    Jm = np.fft.fft(A, axis=0) * (2 / ns)
    for k in range(1, int(RotorMagnets)):
        g3 = (g == (10 + k))
        vmag = v.T @ g3
        Jo = np.dot(Jm, v * g3) / vmag
        Jo2 = np.outer(Jo, g3)
        Jm = Jm - Jo2
    Iphase = np.sqrt(MyIdCurrent ** 2 + MyIqCurrent ** 2) / np.sqrt(2)
    PhaseOhmic = 3 * (PhaseResistance * (1 + TemperatureRise * 0.004)) * Iphase ** 2
    
    results = []

    for thisSpeed in np.arange(SpeedMin, SpeedMax+SpeedStep, SpeedStep):
        thisFrequency = thisSpeed/60  
        w = np.arange(ns)
        w = MyLowestHarmonic * thisFrequency * w * (w < (ns/2))
        
        g1 = (g == 5)
        rotor_loss = symetry_factor*((ch*w + ce*w*w) @ bsq @ (v * g1)) / cs
        g2 = (g == 1)
        stator_loss = symetry_factor*((ch*w + ce*w*w) @ bsq @ (v * g2)) / cs
        
        g4 = (g == 2)
        prox_loss = symetry_factor*((cePhase*w*w) @ bsq @ (v * g4))
        
        magnet_loss = symetry_factor*(1/2) * np.dot((omag*(2*np.pi*w)**2), (np.abs(Jm)**2) @ v)
        total_loss = rotor_loss + stator_loss + prox_loss + PhaseOhmic + magnet_loss
        results.append([thisSpeed, rotor_loss[0], stator_loss[0], magnet_loss[0], PhaseOhmic, prox_loss[0], total_loss[0]])


    column_names = ['thisSpeed', 'rotor_loss', 'stator_loss', 'magnet_loss', 'PhaseOhmic', 'prox_loss', 'total_loss']
    df = pd.DataFrame(results, columns=column_names)

    df.to_csv(datpath, index=False)

    fig1, _ = plt_util.twinPlot({
    "1":{
        'x': df['thisSpeed'], 
        'y': df['rotor_loss'], 
        'label':r'$P_v$ Rotor'
        }, 
    "2":{
        'x': df['thisSpeed'], 
        'y': df['stator_loss'], 
        'label':r'$P_v$ Stator'
        },
    'y1label':r'Verlustleistung in W',
    'x1label':r'Drehzahl in min$^{-1}$',
    })

    w = np.arange(ns)
    w = MyLowestHarmonic * wbase * w * (w < (ns/2))

    g1 = (g == 5)
    ptloss1 =symetry_factor*(((ch * w + ce * w * w) @ bsq) * (g1).T).T / cs

    g2 = (g == 1)
    ptloss2 = symetry_factor*(((ch * w + ce * w * w) @ bsq) * (g2).T).T / cs

    g4 = (g == 2)
    ptloss3 = symetry_factor*(((cePhase * w * w) @ bsq) * (g4).T).T

    ptloss4 = symetry_factor*(1/2) * ((omag * (2 * np.pi * w) ** 2) @ (np.abs(Jm) ** 2)).reshape(-1, 1)
    ptloss = ptloss1 + ptloss2 + ptloss3 + ptloss4

    from matplotlib.patches import Polygon
    from matplotlib.colors import Normalize
    fig2, ax = plt.subplots(figsize=(8, 8))

    cmap = plt_util.cm 
    normalize = Normalize(vmin=ptloss.min(), vmax=ptloss.max())

    for i in range(nn):
        if g[i] == 0:
            continue
        triangle = triag[i]
        result_value = ptloss[i]

        polygon = Polygon(triangle, closed=True, facecolor=cmap(normalize(result_value)))

        ax.add_patch(polygon)

    ax.set_xlim([triag[:,:,0].min(),triag[:,:,0].max()])
    ax.set_ylim([triag[:,:,1].min(),triag[:,:,1].max()])

    fig1.savefig(respath + '_los.eps')
    fig1.savefig(respath + '_los.svg')
    fig1.savefig(respath + '_los.png')
    fig1.savefig(respath + '_los.pdf')
    fig2.savefig(respath + '_img.eps')
    fig2.savefig(respath + '_img.svg')
    fig2.savefig(respath + '_img.png')
    fig2.savefig(respath + '_img.pdf')
    return

def create_image(rotor, params, simname):
    simpath = os.path.join('results', simname, simname + '_steps')
    respath = os.path.join("results", simname, simname + '_img')

    def save_data(filename, *arrays):
        np.savez(filename, *arrays)

    def load_data(filename):
        data = np.load(filename)
        return tuple(data[k] for k in data.files)
    
    runsim = False if os.path.exists(simpath + '.npz') else True 
    if runsim:
        points = multiSimHandler(simulate_point_data, simpath, rotor, params, {'kk':1, 'dk':1, 'RotorMagnets':8, 'MyIdCurrent':0, 'MyIqCurrent':0}, rettype='array')
        nn = points[0]['nn']
       
        g = np.zeros((nn,1)) 
        triag = np.zeros((nn, 3, 2))

        g[:, 0] = points[0]['g']
        triag = points[0]['triag']
        
        save_data(simpath + '.npz', nn, g, triag)
    else:
        loaded_data = load_data(simpath + '.npz')
        nn, g, triag = loaded_data

    from matplotlib.patches import Polygon
    fig, ax = plt.subplots(figsize=(8, 8))

    for i in range(len(triag)):
        triangle_a = triag[i]
        group_a = g[i]

        edges_a = [(tuple(triangle_a[j]), tuple(triangle_a[(j + 1) % 3])) for j in range(3)]
        for edge_a in edges_a:
            draw = True
            start_a, end_a = edge_a
            for j in range(len(triag)):
                if j != i:
                    triangle_b = triag[j]
                    group_b = g[j]

                    edges_b = [(tuple(triangle_b[k]), tuple(triangle_b[(k + 1) % 3])) for k in range(3)]

                    for edge_b in edges_b:
                        start_b, end_b = edge_b

                        if (start_a == start_b and end_a == end_b) or (start_a == end_b and end_a == start_b):
                            if group_a == group_b:
                                draw = False
            if draw:
                ax.plot([start_a[0], end_a[0]], [start_a[1], end_a[1]], color='black')

        polygon = Polygon(triangle_a, closed=True, facecolor='k', edgecolor='none', alpha=0.5)
        ax.add_patch(polygon)

    ax.set_xlim([triag[:, :, 0].min() - 0.5, triag[:, :, 0].max() + 0.5])
    ax.set_ylim([triag[:, :, 1].min() - 0.5, triag[:, :, 1].max() + 0.5])

    fig.savefig(respath + '_img.eps')
    fig.savefig(respath + '_img.svg')
    fig.savefig(respath + '_img.png')
    fig.savefig(respath + '_img.pdf')
    return

def clear_stator():
    mi_selectrectangle(0.1, 0.1, 28.9, 28.9, 4)
    mi_deleteselected()
    mi_clearselected()
    drawArc(16.85, 0, 0, 16.85, angle=90)
    drawLabel(16.2, 0.1, material='Iron')
    drawLabel(16.9, 0.1, material='50JN400')
    drawLabel(16.5, 0.1, material='Air')
    drawLabel(16.7, 0.1, material='Air')
    drawLabel(0.1, 0.1, material='Iron')

def simulate_airgap_flux(rotor, params, simname):
    openfemm()
    if os.path.exists("tmp.fem"):
        os.remove("tmp.fem")
    shutil.copyfile("stator_quater.FEM", "tmp.fem")
    opendocument("tmp.fem")
    clear_stator()
    rotor.create(params)
    mi_analyse(0)
    mi_loadsolution()
    b = []
    magdep = 2.5
    maginset = arcDepth(outer_radius, magdep/2)
    agl = arcAngle(outer_radius, magdep/2)
    nseg = 100
    x = np.linspace(agl, 45-agl, nseg)
    for i in x:
        b.append(mo_getgapb('SlidingBand', i))
    y1 = np.abs([c[0] for c in b])
    y2 = -1*np.max(y1)*np.sin(4*np.deg2rad(x))
    y3 = y2-y1
    closefemm()
    np.savetxt('ideal.csv', y1, delimiter=',')
    plt.plot(x, y1, label='Bist')
    plt.plot(x, y2, label='Bsoll')
    plt.plot(x, y3, label='Bdiff')
    plt.grid()
    plt.show()

def simulate_stator_flux(params, func, filename, sims):
    try:
        redict = params
        retarray = []
        
        openfemm(1)

        if not os.path.exists(filename):
            shutil.copyfile("stator_quater.FEM", filename)
        opendocument(filename)
        
        drawLabel(10, 10, material='50JN400')
        
        mi_modifycircprop('A', 1, redict["irms"]*np.cos(np.deg2rad(redict["degel"])))
        mi_modifycircprop('B', 1, redict["irms"]*np.cos(np.deg2rad(redict["degel"]) + 2/3*np.pi))
        mi_modifycircprop('C', 1, redict["irms"]*np.cos(np.deg2rad(redict["degel"]) - 2/3*np.pi))
        
        mi_analyse(1)
        mi_loadsolution()
        
        b = []
        x = np.linspace(0, 90, 360)
        for i in x:
            b.append(mo_getgapb('SlidingBand', i))        

        mo_close()

        redict.update({"b":[c[0] for c in b], 'x':x})
        retarray.append(dict(redict))

        closefemm()
        return retarray
    except Exception as e:
        try:
            closefemm()
        except Exception:
            pass
        print(e)
        return None

if __name__ == "__main__":
    sys.exit(0)