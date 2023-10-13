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
import modules.plt_util as plt_util
from modules.fem_util import *

params = {}


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
            shutil.copyfile(params['stator_path'], filename)
        
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
            mi_smartmesh(0)
            mi_analyse(1)
            mi_loadsolution()
            mo_smoothoff()
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

        tasks = [executor.submit(process_combo, simfunc, [combo, rotfunc, os.path.join(simpath, str(np.random.randint(1, 0xfffffff)) + ".FEM"), createCombos(sims)]) for combo in combos]
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
                return [item]
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

def simulate_everything(rotor, params, simname, path=None):
    if not os.path.exists(os.path.join('results', simname)):
        os.makedirs(os.path.join('results', simname))
    retdict = {}
    retdict.update(simulate_torque_and_backemf(rotor, params, simname, path=path))
    retdict.update(simulate_torque_moving(rotor, params, simname, path=path))
    return retdict

def simulate_torque_and_backemf(rotor, params, simname, path=None):
    if not os.path.exists(os.path.join(path, 'sims', simname)):
        os.makedirs(os.path.join(path, 'sims', simname))
    simpath = os.path.join('tmp','sims', simname, simname + '_steps')
    csvpath = os.path.join(path,'sims', simname, simname + '_point_static.csv')
    params = params.copy()
    if not os.path.exists(csvpath):
        params.update({
            'degmech': [0, 90, 90*3]
        })
        sims = {
            "irms": 0,
            'degel': 0
        }
        sims.update(params)
        data = multiSimHandler(simulate_general, simpath, rotor.create, params, sims)
        data.to_csv(csvpath, header=True, index=False)

    df = pd.read_csv(csvpath)
    df1 = df[df['irms'] == 0]
    df1.sort_values(by='degmech', inplace=True)
    df1.reset_index(drop=True, inplace=True)

    amin = min(df1['degmech'])
    amax = max(df1['degmech'])
    rotational_speed_rpm = params['rpm']
    ns = rotational_speed_rpm/60
    T = 1/ns
    num_data_points = len(df1)

    dt = (amax-amin)/360*T/num_data_points

    tt = np.arange(0, num_data_points) * dt

    torque = df1['torque_airgap'].values
    aflux = df1['flux_a'].values
    cflux = df1['flux_c'].values
    
    va = params['symmetry_factor'] * np.diff(aflux)/dt
    vc = params['symmetry_factor'] * np.diff(cflux)/dt
    
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
        'label':r'Single Phase Back EMF'
        },
    "4":{
        'x': td, 
        'y': vll, 
        'label':r'Phase-Phase Back EMF'
        },
    'y1label':r'Torque in Nm',
    'y2label':r'Voltage in V',
    'x1label':r'Time in ms',
    }, labelloc='lower center')
    return {'Static Torque': fig}

def simulate_torque_moving(rotor, params, simname, path=None):
    if not os.path.exists(os.path.join(path, 'sims', simname)):
        os.makedirs(os.path.join(path, 'sims', simname))
    simpath = os.path.join('tmp','sims', simname, simname + '_steps')
    csvpath = os.path.join(path,'sims', simname, simname + '_point_movin.csv')
    params = params.copy()
    if not os.path.exists(csvpath):
        params.update({
            'pos':{
                'parameters': {'deg':[0, 90, 90*3]},
                'func': lambda x: {'degel':4*x['deg'], 'degmech':x['deg']+45},
                'mode':'create'
            },
        })
        sims = {
            "irms": np.sqrt(2)*params['irms'],
        }
        sims.update(params)
        data = multiSimHandler(simulate_general, simpath, rotor.create, params, sims)
        data.to_csv(csvpath, header=True, index=False)

    df = pd.read_csv(csvpath)
    df1 = df[df['irms'] == np.sqrt(2)*params['irms']]
    df1.sort_values(by='degmech', inplace=True)
    df1.reset_index(drop=True, inplace=True)

    amin = min(df1['degmech'])
    amax = max(df1['degmech'])
    rotational_speed_rpm = params['rpm']
    ns = rotational_speed_rpm/60
    T = 1/ns
    num_data_points = len(df1)

    dt = (amax-amin)/360*T/num_data_points

    tt = np.arange(0, num_data_points) * dt

    torque = df1['torque_airgap'].values
    aflux = df1['flux_a'].values
    cflux = df1['flux_c'].values
    
    va = params['symmetry_factor'] * np.diff(aflux)/dt
    vc = params['symmetry_factor'] * np.diff(cflux)/dt
    
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
        'label':r'Single Phase Back EMF'
        },
    "4":{
        'x': td, 
        'y': -vll, 
        'label':r'Phase-Phase Back EMF'
        },
    'y1label':r'Torque in Nm',
    'y2label':r'Voltage in V',
    'x1label':r'Time in ms',
    }, labelloc='lower center')
    return {'Torque Moving': fig}

def sweep_1d(rotor, params, simname, labelloc='upper left', path=None):
    if not os.path.exists(os.path.join(path, 'sims', simname)):
        os.makedirs(os.path.join(path, 'sims', simname))
    simpath = os.path.join('tmp','sims', simname, simname + '_steps')
    csvpath1 = os.path.join(path,'sims', simname, simname + '_sweep_stand.csv')
    csvpath2 = os.path.join(path,'sims', simname, simname + '_sweep_movin.csv')
    irms = np.sqrt(2)*params['irms']
    if not os.path.exists(csvpath1):
        sims1 = {
            "irms":(0, irms),
            "degel":0,
            "degmech":[0, 90, 46],
        }
        data1 = multiSimHandler(simulate_general, simpath, rotor.create, params, sims1)
        data1.to_csv(csvpath1, header=True, index=False)
    if not os.path.exists(csvpath2):
        sims2 = {
            "irms":irms,
            'pos':{
                'parameters': {'deg':[0, 90, 46]},
                'func': lambda x: {'degel':4*x['deg'], 'degmech':x['deg']+45},
                'mode':'create'
            },
        }
        data2 = multiSimHandler(simulate_general, simpath, rotor.create, params, sims2)
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

    fig1, _ = plt_util.create_heatmap_interp(sorted_pivot_table_on, xlabel=r"Mechanical Position in Degrees", ylabel=r"Magnet Depth in mm", zlabel=r"Torque in Nm", clevels=10)
    # fig1.savefig(respath + "_on.pdf", bbox_inches='tight')
    # plt.close(fig1)
    
    filtered_data_off = df1[df1['irms'] == 0]

    pivot_table_off = filtered_data_off.pivot_table(
        values='torque_airgap',  
        index='magnet_depth',  
        columns='degmech',       
        aggfunc='first'        
    )

    sorted_pivot_table_off = pivot_table_off.sort_index(ascending=True).sort_index(axis=1, ascending=True)

    fig2, _ = plt_util.create_heatmap_interp(sorted_pivot_table_off, xlabel=r"Mechanical Position in Degrees", ylabel=r"Magnet Depth in mm", zlabel=r"Torque in Nm", clevels=4)
    # fig2.savefig(respath + "_off.pdf", bbox_inches='tight')
    # plt.close(fig2)

    df2 = pd.read_csv(csvpath2)

    filtered_data_rot = df2[df2['irms'] == irms]

    pivot_table_rot = filtered_data_rot.pivot_table(
        values='torque_airgap', 
        index='magnet_depth',   
        columns='degmech',      
        aggfunc='first'         
    )

    sorted_pivot_table_rot = pivot_table_rot.sort_index(ascending=True).sort_index(axis=1, ascending=True)

    fig3, _ = plt_util.create_heatmap_interp(sorted_pivot_table_rot, xlabel=r"Mechanical Position in Degrees", ylabel=r"Magnet Depth in mm", zlabel=r"Torque in Nm", clevels=6)
    # fig3.savefig(respath + "_rot.pdf", bbox_inches='tight')
    # plt.close(fig3)
    
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
            'label':r'$M_{Max}$'
            }, 
        '2':{
            'x': off['magnet_depth'], 
            'y': off['torque_airgap'], 
            'label':r'$M_{Reluctance,max}$'
            }, 
        '3':{
            'x': on['magnet_depth'], 
            'y': combined1[:], 
            'label':r'$\frac{M_{Reluctance,max}}{M_{Max}}$'
            },
        'y1label':r'Torque in Nm',
        'y2label':r'Torque Ripple',
        'x1label':r'Magnet Depth in mm',
        }, labelloc=labelloc)
    # fig4.savefig(respath + "_1da.pdf", bbox_inches='tight')
    # plt.close(fig4)
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
        'y1label':r'Torque in Nm',
        'y2label':r'Torque Ripple',
        'x1label':r'Magnet Dpeth in mm',
        }, labelloc=labelloc)

    # fig5.savefig(respath + "_1db.pdf", bbox_inches='tight')
    # plt.close(fig5)
    return {'Static Torque':fig1, ' Static Reluctance Torque':fig2, 'Dynamic Torque':fig3, 'Torque Max/Reluctance':fig4, 'Torque AC/DC':fig5}

def sweep_2d(rotor, steps, simname, ylabel, xlabel=r"Magnet Depth in mm", path=None):
    if not os.path.exists(os.path.join(path, 'sims', simname)):
        os.makedirs(os.path.join(path, 'sims', simname))
    simpath = os.path.join('tmp','sims', simname, simname + '_steps')
    csvpath1 = os.path.join(path, 'sims', simname, simname + '_sweep_stand.csv')
    csvpath2 = os.path.join(path, 'sims', simname, simname + '_sweep_movin.csv')
    # respath = os.path.join(plt_util.texpath, simname)
    # if not os.path.exists(respath):
    #     os.makedirs(respath)
    # respath = os.path.join(respath, simname)
    
    irms = np.sqrt(2)*steps['irms']
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
                'func': lambda x: {'degel':params['symmetry_factor']*x['deg'], 'degmech':x['deg']},
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
    
    fig1, _ = plt_util.create_heatmap_interp(sorted_pivot_table_on, ylabel=xlabel, xlabel=ylabel, zlabel=r"Torque in Nm")
    # fig1.savefig(respath + "_on.pdf", bbox_inches='tight')
    # plt.close(fig1)
    
    filtered_data_off = df1[df1['irms'] == 0]

    pivot_table_off = filtered_data_off.pivot_table(
        values='torque_airgap', 
        index='x',     
        columns='y',        
        aggfunc='max'          
    )
    sorted_pivot_table_off = pivot_table_off.sort_index(ascending=True).sort_index(axis=1, ascending=True).fillna(0)
    
    fig2, _ = plt_util.create_heatmap_interp(sorted_pivot_table_off, ylabel=xlabel, xlabel=ylabel, zlabel=r"Torque in Nm")
    # fig2.savefig(respath + "_off.pdf", bbox_inches='tight')
    # plt.close(fig2)
    
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

    fig3, _ = plt_util.create_heatmap_interp(sorted_pivot_table_rot, ylabel=xlabel, xlabel=ylabel, zlabel=r"Torque in Nm")
    # fig3.savefig(respath + "_rot_dc.pdf", bbox_inches='tight')
    # plt.close(fig3)
    
    pivot_table_ac = grouped.pivot_table(
        values='ripple',  
        index='x',     
        columns='y',        
        aggfunc='first'        
    )

    sorted_pivot_table_ac = pivot_table_ac.sort_index(ascending=True).sort_index(axis=1, ascending=True).fillna(0)

    fig4, _ = plt_util.create_heatmap_interp(sorted_pivot_table_ac, ylabel=xlabel, xlabel=ylabel, zlabel=r"Torque in Nm")

    # fig4.savefig(respath + "_rot_ac.pdf", bbox_inches='tight')
    # plt.close(fig4)
    tabl1 = (sorted_pivot_table_on/sorted_pivot_table_off).fillna(0)
    table1 = tabl1.applymap(lambda x: constrain(x, 0, 10))
    fig5, _ = plt_util.create_heatmap_interp(table1, ylabel=xlabel, xlabel=ylabel, zlabel=r"$\frac{M_{Max}}{M_{rel,max}}$")
    
    # fig5.savefig(respath + "_ratio.pdf", bbox_inches='tight')
    # plt.close(fig5)
    tabl2 = (sorted_pivot_table_ac/sorted_pivot_table_rot).fillna(0)
    table2 = tabl2.applymap(lambda x: constrain(x, 0, 1))
    fig6, _ = plt_util.create_heatmap_interp(table2, ylabel=xlabel, xlabel=ylabel, zlabel=r"Torque Ripple")
    # fig6.savefig(respath + "_wellig.pdf", bbox_inches='tight')
    # plt.close(fig6)
    return {'Max. Torque': fig1, 'Max. Reluctance Torque': fig2, 'DC Torque Component': fig3, 'AC Torque Component': fig4, 'Torque Ripple': fig6}

if __name__ == "__main__":
    sys.exit(0)