import numpy as np
from scipy.interpolate import RectBivariateSpline
import locale
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
import os, sys

locale.setlocale(locale.LC_NUMERIC, '')
plt_params = {
    'figure.dpi': 72.27,
    'text.usetex': True,
    'text.latex.preamble': r'\usepackage{amsmath} \usepackage{xfrac} \usepackage{eurosym}',
    'font.family': 'sans-serif',
    'axes.labelsize': 32,
    'axes.labelweight': 'bold',
    'font.size': 24,
    'legend.fontsize': 16,
    'xtick.labelsize': 16,
    'ytick.labelsize': 16,
    'xtick.major.pad': 0,
    'ytick.major.pad': 0,
}
plt.rcParams.update(plt_params)

lwidth = 0.5

texpath = os.path.join(os.pardir, os.pardir, "thesis", "ba-laurin-weitzel", "media")
fmt = plt.FuncFormatter(lambda x, _: r'' + f'{{:.3g}}'.format(x).replace('.', ',') + '' if x < 100 else r'' + str(int(x)) + '')

uk_red = (199/255, 16/255, 92/255, 1)
uk_blue = (80/255, 149/255, 200/255, 1)
uk_gold = (234/255, 195/255, 114/255, 1)
uk_green = (74/255, 172/255, 150/255, 1)

colors = [(0, 0, 0.5), (0, 0.5, 1), (0, 1, 1), (0.5, 1, 0.5), (1, 1, 0), (1, 0.5, 0), (1, 0, 0)]
cmap_name = 'rainbw'
cm = LinearSegmentedColormap.from_list(cmap_name, colors, N=256)

def set_size(width=0, pagewidth=False, fraction=1, subplots=(1, 1), ratio=0):
    if width == 0:
        if pagewidth == False:
            width_pt = 426.79135
        else:
            width_pt = 597.50787
    else:
        width_pt = width

    fig_width_pt = width_pt * fraction
    inches_per_pt = 1 / 72.27

    golden_ratio = (5**.5 - 1) / 2 if ratio == 0 else 1/ratio

    fig_width_in = fig_width_pt * inches_per_pt

    fig_height_in = fig_width_in * golden_ratio * (subplots[0] / subplots[1])

    return (fig_width_in, fig_height_in)

def calculate_fontsize(text, min_size, max_width):
    fig, ax = plt.subplots(figsize=(1, 1))
    font_properties = FontProperties()
    text_path = TextPath((0, 0), text, size=min_size, prop=font_properties)

    text_width = text_path.get_extents().width/plt.rcParams['figure.dpi']

    fontsize = min_size

    if text_width > max_width:
        fontsize *= max_width / text_width

    plt.close(fig) 

    return fontsize

def create_heatmap_interp(data, xlabel="", ylabel="", zlabel="", clevels=10, precision=500, fraction=0.7):
    values = data.to_numpy()
    y = data.index.to_numpy()
    x = data.columns.to_numpy()
    x_new = np.linspace(min(x), max(x), precision)
    y_new = np.linspace(min(y), max(y), precision)
    xx, yy = np.meshgrid(x_new, y_new)

    interp_func = RectBivariateSpline(y, x, values)  
    interpolated_data = interp_func(y_new, x_new)  

    fig = plt.figure()
    ax = fig.subplots()
    heatmap = ax.imshow(interpolated_data, extent=(min(x), max(x), min(y), max(y)),  
            origin='lower', cmap=cm, aspect='auto')

    contour_levels = np.linspace(interpolated_data.min(), interpolated_data.max(), clevels + 2)
    contour = ax.contour(xx, yy, interpolated_data, levels=contour_levels, colors='black', linewidths=lwidth)

    ax.clabel(contour, inline=True, fontsize=10, fmt=fmt)

    cbar = fig.colorbar(heatmap)
    cbar.set_label(r'' + zlabel + r'', labelpad=1)
    cbar.set_ticks(contour_levels)
    cbar.formatter = fmt
    cbar.ax.tick_params(axis='both', which='major', pad=1, length=2)

    ax.set_xlabel(r'' + xlabel + r'', labelpad=1)
    ax.set_ylabel(r'' + ylabel + r'', labelpad=1)
    ax.tick_params(axis='both', which='major', pad=1, length=2)

    ax.xaxis.set_major_formatter(fmt)
    ax.yaxis.set_major_formatter(fmt)

    fig.tight_layout(pad=1, h_pad=None, w_pad=None, rect=None)

    return fig, ax

def twinPlot(data, axis=None, fraction=0.49, ratio=0, labelloc='upper left'):
    if axis is None:
        fig = plt.figure()
        gs = GridSpec(
            1,
            1
        )
        
    dat1 = data["1"] if "1" in data else None
    dat2 = data["2"] if "2" in data else None
    dat3 = data["3"] if "3" in data else None
    dat4 = data["4"] if "4" in data else None
    col1 = data["col1"] if "col1" in data else uk_red
    col2 = data["col2"] if "col2" in data else uk_blue
    y1label = data['y1label'] if 'y1label' in data else ''
    y2label = data['y2label'] if 'y2label' in data else ''
    x1label = data['x1label'] if 'x1label' in data else ''
    
    if axis is None:
        ax1 = fig.add_subplot(gs[0, 0])
    else:
        ax1 = axis
    if dat1 is not None:
        ax1.plot(dat1["x"], dat1["y"], linewidth=lwidth, color=col1, label=r'' + dat1["label"])
    if dat2 is not None:
        ax1.plot(dat2["x"], dat2["y"], linewidth=lwidth, color=col1, linestyle='dashed', label=r'' + dat2["label"])
    if dat3 is not None:
        ax1.plot(np.nan, linewidth=lwidth, color=col2, label=r'' + dat3["label"])
    if dat4 is not None:
        ax1.plot(np.nan, linewidth=lwidth, color=col2, linestyle='dashed', label=r'' + dat4["label"])
    if dat3 is not None or dat4 is not None:
        ax2 = ax1.twinx()
    if dat3 is not None:
        ax2.plot(dat3["x"], dat3["y"], linewidth=lwidth, color=col2)
    if dat4 is not None:
        ax2.plot(dat4["x"], dat4["y"], linewidth=lwidth, color=col2, linestyle='dashed')
    if 'y2label' in data:
        ax2.set_ylabel(r'' + y2label, labelpad=1)
        ax2.yaxis.set_major_formatter(fmt)
        ax2.tick_params(axis='y', which='major', pad=1, length=2)
    ax1.grid(zorder=1, linewidth=lwidth*3/4)
    for line in ax1.lines:
        line.set_zorder(2) 
    for line in ax2.lines:
        line.set_zorder(2) 

    legend = plt.legend(*(ax1.get_legend_handles_labels()), fontsize=plt.rcParams['legend.fontsize'], loc=labelloc)
    legend.set_zorder(3)
    legend.get_frame().set_linewidth(lwidth)
    ax2.add_artist(legend)
    if 'y1label' in data:
        ax1.set_ylabel(r'' + y1label, labelpad=1)
        ax1.yaxis.set_major_formatter(fmt)
    if 'x1label' in data:
        ax1.set_xlabel(r'' + x1label, labelpad=1)
        ax1.xaxis.set_major_formatter(fmt)
        ax1.tick_params(axis='both', which='major', pad=1, length=2)
    ax1.set_xlim([
        min(min(v) for v in [d['x'] for d in [dat1, dat2, dat3, dat4] if d is not None]),
        max(max(v) for v in [d['x'] for d in [dat1, dat2, dat3, dat4] if d is not None])
    ])
    ax1.yaxis.label.set_color(col1)
    if dat3 is not None or dat4 is not None:
        ax2.yaxis.label.set_color(col2)
    else:
        ax2 = None
    fig.tight_layout(pad=1, h_pad=None, w_pad=None, rect=None)
    if axis is None:
        return fig, [ax1, ax2]
    else:
        return [ax1, ax2]

def quadPlot(data):
    fig = plt.figure(figsize=(8, 6))
    gs = GridSpec(
        2,
        1
    )

    col1 = data["col1"] if "col1" in data else uk_red
    col2 = data["col2"] if "col2" in data else uk_gold
    col3 = data["col3"] if "col3" in data else uk_blue
    col4 = data["col4"] if "col4" in data else uk_green

    keys = {'5':'1', '6':'2', '7':'3', '8':'4', 'col3':'col1', 'col4':'col2', 'y3label':'y1label', 'y4label':'y2label', 'x2label':'x1label'}
    
    dict1 = {
        key: value for key, value in data.items() if key in (
            "1", "2", "3", "4", "y1label", "y2label", "x1label"
        )
    }
    dict1.update({'col1':col1, 'col2':col2})
    dict2 = {
        keys[key]: value for key, value in data.items() if key in (
            "5", "6", "7", "8", "y3label", "y4label", "x2label"
        )
    }
    dict2.update({'col1':col3, 'col2':col4})

    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    ax11, ax12 = twinPlot(dict1, axis=ax1)
    ax21, ax22 = twinPlot(dict2, axis=ax2)

    fig.tight_layout(pad=0.05)
    
    return fig, [ax11, ax12, ax21, ax22]

def barPlot(data):
    col1 = data["col1"] if "col1" in data else uk_red
    col2 = data["col2"] if "col2" in data else uk_blue
    col3 = data["col3"] if "col3" in data else uk_gold
    col4 = data["col4"] if "col4" in data else uk_green
    
    ylabel = data['ylabel'] if 'ylabel' in data else ''
    xlabel = data['xlabel'] if 'xlabel' in data else ''
    ylim = data['ylim'] if 'ylim' in data else None

    x = np.array(data['x'])
    y1 = np.array(data['y1']) if 'y1' in data else None
    y2 = np.array(data['y2']) if 'y2' in data else None
    y3 = np.array(data['y3']) if 'y3' in data else None
    y4 = np.array(data['y4']) if 'y4' in data else None

    yfntsze = calculate_fontsize(r''+ylabel, plt.rcParams['axes.labelsize'], set_size(fraction=0.6, ratio=2)[1]*0.95)

    xticks = data['xticks'] if 'xticks' in data else None
    barnum = (1 if y1 is not None else 0)+(1 if y2 is not None else 0)+(1 if y3 is not None else 0)+(1 if y4 is not None else 0)
    if barnum == 0:
        return
    
    barwidth = 1/(barnum+1)

    fig, ax = plt.subplots(figsize=set_size(fraction=0.6, ratio=2))
    ax.grid(axis='y', zorder=0, linewidth=lwidth*3/4)
    pos = np.arange(len(x))
    i = 1
    if y1 is not None:
        ax.bar(pos + barwidth*i, y1, barwidth, color=col1, edgecolor='black', linewidth=lwidth, zorder=10, label=data['yl1'] if 'yl1' in data else '')
        i += 1
    if y2 is not None:
        ax.bar(pos + barwidth*i, y2, barwidth, color=col2, edgecolor='black', linewidth=lwidth, zorder=10, label=data['yl2'] if 'yl2' in data else '')
        i += 1
    if y3 is not None:
        ax.bar(pos + barwidth*i, y3, barwidth, color=col3, edgecolor='black', linewidth=lwidth, zorder=10, label=data['yl3'] if 'yl3' in data else '')
        i += 1
    if y4 is not None:
        ax.bar(pos + barwidth*i, y4, barwidth, color=col4, edgecolor='black', linewidth=lwidth, zorder=10, label=data['yl4'] if 'yl4' in data else '')
        i += 1

    ax.set_xticks(pos + 0.5, xticks if xticks is not None else [str(b) for b in x])
    ax.set_ylabel(r'' + ylabel, fontsize=yfntsze, labelpad=1)
    ax.set_xlabel(r'' + xlabel, fontsize=yfntsze, labelpad=1)
    ax.tick_params(axis='both', which='major', pad=1, length=2)
    legend = ax.legend(fontsize=plt.rcParams['legend.fontsize'], loc='upper right')
    legend.set_zorder(15)
    legend.get_frame().set_linewidth(lwidth)
    ax.yaxis.set_major_formatter(fmt)
    if ylim is not None:
        ax.set_ylim(ylim)
    fig.tight_layout(pad=0.05, h_pad=None, w_pad=None, rect=None)

    if 'name' in data and 'folder' in data:
        respath = os.path.join(texpath, data['folder'])
        if not os.path.exists(respath):
            os.makedirs(respath)
        fig.savefig(os.path.join(respath, data['name'] + '.pdf'))
        plt.close(fig)

    return fig, ax

if __name__ == "__main__":
    print(plt.rcParams.keys())
    sys.exit(0)
