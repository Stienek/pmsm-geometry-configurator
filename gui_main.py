import sys, os, shutil
import json
import zlib
import threading

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import qdarktheme as qd

default_application_settings = {
    'window_width': 800,
    'window_height': 600,
    'window_position_x': 100,
    'window_position_y': 100,
}

new_project_index = 0
simid = 0

os.chdir(os.path.dirname(sys.argv[0]))
from modules.plt_util import *
from modules.sim_util import *
from modules.fem_util import *

import geometries.initial_gen as initial
import geometries.burried_gen as burried
import geometries.spoke_gen as spoke
import geometries.vera_gen as vera
import geometries.ITHMA_gen as halbach

class SettingsManager:
    def __init__(self, file_path, initial_settings={}):
        self.file_path = file_path
        try:
            with open(self.file_path, 'r') as file:
                self.data = json.load(file)
        except FileNotFoundError:
            self.data = initial_settings
        self.save()

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value        
        self.save()
        
    def __contains__(self, key):
        return key in self.data

    def update(self, new_data):
        self.data.update(new_data)
        self.save()

    def __repr__(self):
        return repr(self.data)
    
    def save(self):
        with open(self.file_path, 'w') as file:
            json.dump(self.data, file, indent=4)

class PMSMFileHandler:
    def __init__(self, folder_path):
        self.folder_path = folder_path

    def _read_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def _write_file(self, file_path, content):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)

    def pack(self, output_file):
        data = {}
        for foldername, _, filenames in os.walk(self.folder_path):
            folder_data = {}
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                file_content = self._read_file(file_path)
                folder_data[filename] = file_content
            data[os.path.relpath(foldername, self.folder_path)] = folder_data

        with open(output_file, 'wb') as file:
            json_data = json.dumps(data).encode('utf-8')
            compressed_data = zlib.compress(json_data)
            file.write(compressed_data)

    def unpack(self, input_file):
        with open(input_file, 'rb') as file:
            compressed_data = file.read()
            json_data = zlib.decompress(compressed_data)
            data = json.loads(json_data.decode('utf-8'))

        for rel_folder_path, folder_data in data.items():
            folder_path = os.path.join(self.folder_path, rel_folder_path)
            for filename, content in folder_data.items():
                file_path = os.path.join(folder_path, filename)
                self._write_file(file_path, content)


class MatplotlibWidget(QWidget):
    def __init__(self, fig):
        super().__init__()
        self.figure = fig
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.canvas)
        self.layout.addWidget(self.toolbar)
        self.setLayout(self.layout)
        self.plot_random_data()

    def plot_random_data(self):
        self.canvas.draw()

    def close(self):
        plt.close(self.figure)

class FileWidget(QSplitter):
    def __init__(self, parent, name=None, path=None):
        super().__init__(parent)
        self.save_path = None
        self.parent = parent
        self.save_required = True
        if path == None:
            if name == None:
                raise AttributeError("FileWidget either needs a name or a path to a project.")
            self.tmp_project_path = os.path.join('tmp', name)
            os.mkdir(self.tmp_project_path)
        else:
            if not os.path.exists(path):
                raise FileNotFoundError("The specified project does not exist.")
            self.tmp_project_path = os.path.join('tmp', os.path.basename(path).split('.')[0])
            self.save_path = path
            load_file = PMSMFileHandler(self.tmp_project_path)
            load_file.unpack(self.save_path)
            
        self.settings = SettingsManager(os.path.join(self.tmp_project_path, "settings.json"), initial_settings={'project_name':name})
        
        self.results = []
        if 'simulations' not in self.settings:
            self.settings['simulations'] = []
        if 'spmsweepname' not in self.settings:
            self.settings['spmsweepname'] = "surface_magnet_sweep"
        if 'spmpointname' not in self.settings:
            self.settings['spmpointname'] = "surface_magnet_point"
        if 'ipmrsweepname' not in self.settings:
            self.settings['ipmrsweepname'] = "burried_magnet_sweep"
        if 'ipmrpointname' not in self.settings:
            self.settings['ipmrpointname'] = "burried_magnet_point"
        if 'ipmtsweepname' not in self.settings:
            self.settings['ipmtsweepname'] = "spoke_config_sweep"
        if 'ipmtpointname' not in self.settings:
            self.settings['ipmtpointname'] = "spoke_config_point"
        if 'ipmvsweepname' not in self.settings:
            self.settings['ipmvsweepname'] = "v_config_sweep"
        if 'ipmvpointname' not in self.settings:
            self.settings['ipmvpointname'] = "v_config_point"
        if 'halbachsweepname' not in self.settings:
            self.settings['halbachsweepname'] = "halbach_array_sweep"
        if 'halbachpointname' not in self.settings:
            self.settings['halbachpointname'] = "halbach_array_point"
        if 'ithmasweepname' not in self.settings:
            self.settings['ithmasweepname'] = "ithma_sweep"
        if 'ithmapointname' not in self.settings:
            self.settings['ithmapointname'] = "ithma_point"

        
        if 'stator_path' not in self.settings:
            self.settings['stator_path'] = ''
        if 'inner_radius' not in self.settings:
            self.settings['inner_radius'] = 5
        if 'outer_radius' not in self.settings:
            self.settings['outer_radius'] = 16.1
        if 'stator_poles' not in self.settings:
            self.settings['stator_poles'] = 12
        if 'rotor_poles' not in self.settings:
            self.settings['rotor_poles'] = 8
        if 'symmetry_factor' not in self.settings:
            self.settings['symmetry_factor'] = 4
        if 'irms' not in self.settings:
            self.settings['irms'] = 12
        if 'degoffset' not in self.settings:
            self.settings['degoffset'] = 22.5
        if 'spmsweepstart' not in self.settings:
            self.settings['spmsweepstart'] = 0.1
        if 'spmsweepend' not in self.settings:
            self.settings['spmsweepend'] = 8
        if 'spmsweepstep' not in self.settings:
            self.settings['spmsweepstep'] = 24
        if 'spmpointdepth' not in self.settings:
            self.settings['spmpointdepth'] = 2.6
        if 'ipmrsweepstart' not in self.settings:
            self.settings['ipmrsweepstart'] = 0.1
        if 'ipmrsweepend' not in self.settings:
            self.settings['ipmrsweepend'] = 8
        if 'ipmrsweepstep' not in self.settings:
            self.settings['ipmrsweepstep'] = 24
        if 'ipmrpointdepth' not in self.settings:
            self.settings['ipmrpointdepth'] = 2.95
        if 'ipmtsweepstart' not in self.settings:
            self.settings['ipmtsweepstart'] = 0.1
        if 'ipmtsweepend' not in self.settings:
            self.settings['ipmtsweepend'] = 3
        if 'ipmtsweepstep' not in self.settings:
            self.settings['ipmtsweepstep'] = 24
        if 'ipmtpointdepth' not in self.settings:
            self.settings['ipmtpointdepth'] = 2.5
        if 'ipmvsweepstart1' not in self.settings:
            self.settings['ipmvsweepstart1'] = 0.1
        if 'ipmvsweepend1' not in self.settings:
            self.settings['ipmvsweepend1'] = 3.5
        if 'ipmvsweepstep1' not in self.settings:
            self.settings['ipmvsweepstep1'] = 24
        if 'ipmvsweepstart2' not in self.settings:
            self.settings['ipmvsweepstart2'] = 0.1
        if 'ipmvsweepend2' not in self.settings:
            self.settings['ipmvsweepend2'] = 45
        if 'ipmvsweepstep2' not in self.settings:
            self.settings['ipmvsweepstep2'] = 24
        if 'ipmvpointdepth' not in self.settings:
            self.settings['ipmvpointdepth'] = 2.25
        if 'ipmvpointangle' not in self.settings:
            self.settings['ipmvpointangle'] = 12.5
        if 'halbachsweepside' not in self.settings:
            self.settings['halbachsweepside'] = "A"
        if 'halbachsweepstart1' not in self.settings:
            self.settings['halbachsweepstart1'] = 0.1
        if 'halbachsweepend1' not in self.settings:
            self.settings['halbachsweepend1'] = 5
        if 'halbachsweepstep1' not in self.settings:
            self.settings['halbachsweepstep1'] = 12
        if 'halbachsweepstart2' not in self.settings:
            self.settings['halbachsweepstart2'] = 0.01
        if 'halbachsweepend2' not in self.settings:
            self.settings['halbachsweepend2'] = 0.99
        if 'halbachsweepstep2' not in self.settings:
            self.settings['halbachsweepstep2'] = 12
        if 'halbachpointside' not in self.settings:
            self.settings['halbachpointside'] = "A"
        if 'halbachpointdepth' not in self.settings:
            self.settings['halbachpointdepth'] = 3
        if 'halbachpointratio' not in self.settings:
            self.settings['halbachpointratio'] = 0.25
        
        if 'ithmasweepside' not in self.settings:
            self.settings['ithmasweepside'] = "A"
        if 'ithmasweepdepth' not in self.settings:
            self.settings['ithmasweepdepth'] = 3
        if 'ithmasweepratio' not in self.settings:
            self.settings['ithmasweepratio'] = 12.5
        if 'ithmasweepstart3' not in self.settings:
            self.settings['ithmasweepstart3'] = -20
        if 'ithmasweepend3' not in self.settings:
            self.settings['ithmasweepend3'] = 20
        if 'ithmasweepstep3' not in self.settings:
            self.settings['ithmasweepstep3'] = 12
        if 'ithmasweepstart4' not in self.settings:
            self.settings['ithmasweepstart4'] = -45
        if 'ithmasweepend4' not in self.settings:
            self.settings['ithmasweepend4'] = 45
        if 'ithmasweepstep4' not in self.settings:
            self.settings['ithmasweepstep4'] = 12
        if 'ithmapointside' not in self.settings:
            self.settings['ithmapointside'] = "A"
        if 'ithmapointdepth' not in self.settings:
            self.settings['ithmapointdepth'] = 3
        if 'ithmapointratio' not in self.settings:
            self.settings['ithmapointratio'] = 0.25
        if 'ithmapointangle' not in self.settings:
            self.settings['ithmapointangle'] = 0
        if 'ithmapointmagangle' not in self.settings:
            self.settings['ithmapointmagangle'] = 0
        
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.hlayout = QSplitter(Qt.Orientation.Horizontal)
        self.addWidget(self.hlayout)
        self.hlayout.setStretchFactor(0, 1)
        self.hlayout.setStretchFactor(1, 2)
        self.hlayout.setStretchFactor(2, 1)
        self.hlayout.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.setup_widget = QTabWidget(self)
        self.setup_widget.setTabPosition(QTabWidget.TabPosition.West) 
        self.setup_widget.setMovable(False) 
        self.setup_widget.setTabsClosable(False)
        self.hlayout.addWidget(self.setup_widget)

        self.setup_general_widget = QWidget(self)
        self.setup_general_layout = QVBoxLayout()
        self.setup_general_widget.setLayout(self.setup_general_layout)
        self.setup_widget.addTab(self.setup_general_widget, "General")

        if os.path.exists(os.path.join(self.tmp_project_path, 'stator.FEM')):
            istatorlabel = self.settings['stator_path']
            self.settings.save()
        else:
            istatorlabel = ''
        self.setup_general_fname_label = QLabel(f"Stator File: {istatorlabel}")
        self.setup_general_fname_button = QPushButton("Select new File")
        self.setup_general_fname_button.pressed.connect(self.setup_general_fname_select)
        self.setup_general_layout.addWidget(self.setup_general_fname_label)
        self.setup_general_layout.addWidget(self.setup_general_fname_button)

        self.inner_radius_label = QLabel("Inner Radius:")
        self.inner_radius_input = QDoubleSpinBox()
        self.inner_radius_input.setValue(self.settings['inner_radius'])
        self.setup_general_layout.addWidget(self.inner_radius_label)
        self.setup_general_layout.addWidget(self.inner_radius_input)
        self.inner_radius_input.valueChanged.connect(lambda x: self.update_settings('inner_radius', x))

        self.outer_radius_label = QLabel("Outer Radius:")
        self.outer_radius_input = QDoubleSpinBox()
        self.outer_radius_input.setValue(self.settings['outer_radius'])
        self.setup_general_layout.addWidget(self.outer_radius_label)
        self.setup_general_layout.addWidget(self.outer_radius_input)
        self.outer_radius_input.valueChanged.connect(lambda x: self.update_settings('outer_radius', x))

        self.stator_poles_label = QLabel("Stator Poles:")
        self.stator_poles_input = QSpinBox()
        self.stator_poles_input.setValue(self.settings['stator_poles'])
        self.setup_general_layout.addWidget(self.stator_poles_label)
        self.setup_general_layout.addWidget(self.stator_poles_input)
        self.stator_poles_input.valueChanged.connect(lambda x: self.update_settings('stator_poles', x))

        self.rotor_poles_label = QLabel("Rotor Poles:")
        self.rotor_poles_input = QSpinBox()
        self.rotor_poles_input.setValue(self.settings['rotor_poles'])
        self.setup_general_layout.addWidget(self.rotor_poles_label)
        self.setup_general_layout.addWidget(self.rotor_poles_input)
        self.rotor_poles_input.valueChanged.connect(lambda x: self.update_settings('rotor_poles', x))

        self.symmetry_factor_label = QLabel("Symmetry Factor:")
        self.symmetry_factor_input = QSpinBox()
        self.symmetry_factor_input.setValue(self.settings['symmetry_factor'])
        self.setup_general_layout.addWidget(self.symmetry_factor_label)
        self.setup_general_layout.addWidget(self.symmetry_factor_input)
        self.symmetry_factor_input.valueChanged.connect(lambda x: self.update_settings('symmetry_factor', x))

        self.current_label = QLabel("Nominal RMS Current:")
        self.current_input = QDoubleSpinBox()
        self.current_input.setValue(self.settings['irms'])
        self.setup_general_layout.addWidget(self.current_label)
        self.setup_general_layout.addWidget(self.current_input)
        self.current_input.valueChanged.connect(lambda x: self.update_settings('irms', x))

        self.d_position_label = QLabel("Angle Offset from d-Axis:")
        self.d_position_input = QDoubleSpinBox()
        self.d_position_input.setValue(self.settings['degoffset'])
        self.setup_general_layout.addWidget(self.d_position_label)
        self.setup_general_layout.addWidget(self.d_position_input)
        self.d_position_input.valueChanged.connect(lambda x: self.update_settings('degoffset', x))

        self.setup_spm_widget = QWidget(self)
        self.setup_spm_layout = QVBoxLayout()
        self.setup_spm_widget.setLayout(self.setup_spm_layout)
        self.setup_widget.addTab(self.setup_spm_widget, "Surface Magnets")
        
        self.spm_sweep_label0 = QLabel("Parameter Sweep Simulation Name")
        self.spm_sweep_name = QLineEdit(self.settings['spmsweepname'])
        self.spm_range_label1 = QLabel("Magnet Depth:")
        self.spm_range_label2 = QLabel("Start:")
        self.spm_range_label3 = QLabel("End:")
        self.spm_range_label4 = QLabel("Steps:")
        self.spm_range_layout = QHBoxLayout()
        self.spm_range_widget = QWidget()
        self.spm_range_widget.setLayout(self.spm_range_layout)
        self.spm_range_start = QDoubleSpinBox()
        self.spm_range_start.setValue(self.settings['spmsweepstart'])
        self.spm_range_end = QDoubleSpinBox()
        self.spm_range_end.setValue(self.settings['spmsweepend'])
        self.spm_range_step = QSpinBox()
        self.spm_range_step.setValue(self.settings['spmsweepstep'])
        self.setup_spm_layout.addWidget(self.spm_sweep_label0)
        self.setup_spm_layout.addWidget(self.spm_sweep_name)
        self.setup_spm_layout.addWidget(self.spm_range_label1)
        self.setup_spm_layout.addWidget(self.spm_range_widget)
        self.spm_range_layout.addWidget(self.spm_range_label2)
        self.spm_range_layout.addWidget(self.spm_range_start, 1)
        self.spm_range_layout.addWidget(self.spm_range_label3)
        self.spm_range_layout.addWidget(self.spm_range_end, 1)
        self.spm_range_layout.addWidget(self.spm_range_label4)
        self.spm_range_layout.addWidget(self.spm_range_step, 1)
        self.spm_sweep_name.textChanged.connect(lambda x: self.update_settings('spmsweepname', x))
        self.spm_range_start.valueChanged.connect(lambda x: self.update_settings('spmsweepstart', x))
        self.spm_range_end.valueChanged.connect(lambda x: self.update_settings('spmsweepend', x))
        self.spm_range_step.valueChanged.connect(lambda x: self.update_settings('spmsweepstep', x))
        self.spm_sweep_button = QPushButton("Add Surface Magnets Sweep to Queue")
        self.spm_sweep_button.pressed.connect(lambda: self.add_simulation({'type':'sweep', 'parameters':['initial', {'magnet_depth':[self.settings['spmsweepstart'], self.settings['spmsweepend'], self.settings['spmsweepstep']]}, self.settings['spmsweepname']]}))
        self.setup_spm_layout.addWidget(self.spm_sweep_button)
        
        self.spm_point_label0 = QLabel("Single Point Simulation Name:")
        self.spm_point_name = QLineEdit(self.settings['spmpointname'])
        self.spm_point_label1 = QLabel("Magnet Depth:")
        self.spm_point_pos = QDoubleSpinBox()
        self.spm_point_pos.setValue(self.settings['spmpointdepth'])
        self.spm_point_button = QPushButton("Add Surface Magnets Point Simulation to Queue")
        self.setup_spm_layout.addWidget(self.spm_point_label0)
        self.setup_spm_layout.addWidget(self.spm_point_name)
        self.setup_spm_layout.addWidget(self.spm_point_label1)
        self.setup_spm_layout.addWidget(self.spm_point_pos)
        self.setup_spm_layout.addWidget(self.spm_point_button)
        self.spm_point_name.textChanged.connect(lambda x: self.update_settings('spmpointname', x))
        self.spm_point_pos.valueChanged.connect(lambda x: self.update_settings('spmpointdepth', x))
        self.spm_point_button.pressed.connect(lambda: self.add_simulation({'type':'point', 'parameters':['initial', {'magnet_depth':self.settings['spmpointdepth']}, self.settings['spmpointname']]}))

        self.setup_ipmr_widget = QWidget(self)
        self.setup_ipmr_layout = QVBoxLayout()
        self.setup_ipmr_widget.setLayout(self.setup_ipmr_layout)
        self.setup_widget.addTab(self.setup_ipmr_widget, "Burried Magnets")

        self.ipmr_sweep_label0 = QLabel("Parameter Sweep Simulation Name:")
        self.ipmr_sweep_name = QLineEdit(self.settings['ipmrsweepname'])
        self.ipmr_range_label1 = QLabel("Magnet Depth:")
        self.ipmr_range_label2 = QLabel("Start:")
        self.ipmr_range_label3 = QLabel("End:")
        self.ipmr_range_label4 = QLabel("Steps:")
        self.ipmr_range_layout = QHBoxLayout()
        self.ipmr_range_widget = QWidget()
        self.ipmr_range_widget.setLayout(self.ipmr_range_layout)
        self.ipmr_range_start = QDoubleSpinBox()
        self.ipmr_range_start.setValue(self.settings['ipmrsweepstart'])
        self.ipmr_range_end = QDoubleSpinBox()
        self.ipmr_range_end.setValue(self.settings['ipmrsweepend'])
        self.ipmr_range_step = QSpinBox()
        self.ipmr_range_step.setValue(self.settings['ipmrsweepstep'])
        self.setup_ipmr_layout.addWidget(self.ipmr_sweep_label0)
        self.setup_ipmr_layout.addWidget(self.ipmr_sweep_name)
        self.setup_ipmr_layout.addWidget(self.ipmr_range_label1)
        self.setup_ipmr_layout.addWidget(self.ipmr_range_widget)
        self.ipmr_range_layout.addWidget(self.ipmr_range_label2)
        self.ipmr_range_layout.addWidget(self.ipmr_range_start, 1)
        self.ipmr_range_layout.addWidget(self.ipmr_range_label3)
        self.ipmr_range_layout.addWidget(self.ipmr_range_end, 1)
        self.ipmr_range_layout.addWidget(self.ipmr_range_label4)
        self.ipmr_range_layout.addWidget(self.ipmr_range_step, 1)

        self.ipmr_sweep_name.textChanged.connect(lambda x: self.update_settings('ipmrsweepname', x))
        self.ipmr_range_start.valueChanged.connect(lambda x: self.update_settings('ipmrsweepstart', x))
        self.ipmr_range_end.valueChanged.connect(lambda x: self.update_settings('ipmrsweepend', x))
        self.ipmr_range_step.valueChanged.connect(lambda x: self.update_settings('ipmrsweepstep', x))
        self.ipmr_sweep_button = QPushButton("Add Burried Magnet Sweep to Queue")
        self.ipmr_sweep_button.pressed.connect(lambda: self.add_simulation({'type':'sweep', 'parameters':['burried', {'magnet_depth':[self.settings['ipmrsweepstart'], self.settings['ipmrsweepend'], self.settings['ipmrsweepstep']]}, self.settings['ipmrsweepname']]}))
        self.setup_ipmr_layout.addWidget(self.ipmr_sweep_button)
        
        self.ipmr_point_label0 = QLabel("Single Point Simulation Name:")
        self.ipmr_point_name = QLineEdit(self.settings['ipmrpointname'])
        self.ipmr_point_label1 = QLabel("Magnet Depth:")
        self.ipmr_point_pos = QDoubleSpinBox()
        self.ipmr_point_pos.setValue(self.settings['ipmrpointdepth'])
        self.ipmr_point_button = QPushButton("Add Burried Magnet Point Simulation to Queue")
        self.setup_ipmr_layout.addWidget(self.ipmr_point_label0)
        self.setup_ipmr_layout.addWidget(self.ipmr_point_name)
        self.setup_ipmr_layout.addWidget(self.ipmr_point_label1)
        self.setup_ipmr_layout.addWidget(self.ipmr_point_pos)
        self.setup_ipmr_layout.addWidget(self.ipmr_point_button)
        self.ipmr_point_name.textChanged.connect(lambda x: self.update_settings('ipmrpointname', x))
        self.ipmr_point_pos.valueChanged.connect(lambda x: self.update_settings('ipmrpointdepth', x))
        self.ipmr_point_button.pressed.connect(lambda: self.add_simulation({'type':'point', 'parameters':['burried', {'magnet_depth':self.settings['ipmrpointdepth']}, self.settings['ipmrpointname']]}))

        self.setup_ipmt_widget = QWidget(self)
        self.setup_ipmt_layout = QVBoxLayout()
        self.setup_ipmt_widget.setLayout(self.setup_ipmt_layout)
        self.setup_widget.addTab(self.setup_ipmt_widget, "Spoke Configuration")

        self.ipmt_sweep_label0 = QLabel("Parameter Sweep Simulation Name:")
        self.ipmt_sweep_name = QLineEdit(self.settings['ipmtsweepname'])
        self.ipmt_range_label1 = QLabel("Magnet Depth:")
        self.ipmt_range_label2 = QLabel("Start:")
        self.ipmt_range_label3 = QLabel("End:")
        self.ipmt_range_label4 = QLabel("Steps:")
        self.ipmt_range_layout = QHBoxLayout()
        self.ipmt_range_widget = QWidget()
        self.ipmt_range_widget.setLayout(self.ipmt_range_layout)
        self.ipmt_range_start = QDoubleSpinBox()
        self.ipmt_range_start.setValue(self.settings['ipmtsweepstart'])
        self.ipmt_range_end = QDoubleSpinBox()
        self.ipmt_range_end.setValue(self.settings['ipmtsweepend'])
        self.ipmt_range_step = QSpinBox()
        self.ipmt_range_step.setValue(self.settings['ipmtsweepstep'])
        self.setup_ipmt_layout.addWidget(self.ipmt_sweep_label0)
        self.setup_ipmt_layout.addWidget(self.ipmt_sweep_name)
        self.setup_ipmt_layout.addWidget(self.ipmt_range_label1)
        self.setup_ipmt_layout.addWidget(self.ipmt_range_widget)
        self.ipmt_range_layout.addWidget(self.ipmt_range_label2)
        self.ipmt_range_layout.addWidget(self.ipmt_range_start, 1)
        self.ipmt_range_layout.addWidget(self.ipmt_range_label3)
        self.ipmt_range_layout.addWidget(self.ipmt_range_end, 1)
        self.ipmt_range_layout.addWidget(self.ipmt_range_label4)
        self.ipmt_range_layout.addWidget(self.ipmt_range_step, 1)
        self.ipmt_sweep_name.textChanged.connect(lambda x: self.update_settings('ipmtsweepname', x))
        self.ipmt_range_start.valueChanged.connect(lambda x: self.update_settings('ipmtsweepstart', x))
        self.ipmt_range_end.valueChanged.connect(lambda x: self.update_settings('ipmtsweepend', x))
        self.ipmt_range_step.valueChanged.connect(lambda x: self.update_settings('ipmtsweepstep', x))
        self.ipmt_sweep_button = QPushButton("Add Spoke Configuration Sweep to Queue")
        self.ipmt_sweep_button.pressed.connect(lambda: self.add_simulation({'type':'sweep', 'parameters':['spoke', {'magnet_depth':[self.settings['ipmtsweepstart'], self.settings['ipmtsweepend'], self.settings['ipmtsweepstep']]}, self.settings['ipmtsweepname']]}))
        self.setup_ipmt_layout.addWidget(self.ipmt_sweep_button)
        
        self.ipmt_point_label0 = QLabel("Single Point Simulation Name:")
        self.ipmt_point_name = QLineEdit(self.settings['ipmtpointname'])
        self.ipmt_point_label1 = QLabel("Magnet Depth:")
        self.ipmt_point_pos = QDoubleSpinBox()
        self.ipmt_point_pos.setValue(self.settings['ipmtpointdepth'])
        self.ipmt_point_button = QPushButton("Add Spoke Configuration Point Simulation to Queue")
        self.setup_ipmt_layout.addWidget(self.ipmt_point_label0)
        self.setup_ipmt_layout.addWidget(self.ipmt_point_name)
        self.setup_ipmt_layout.addWidget(self.ipmt_point_label1)
        self.setup_ipmt_layout.addWidget(self.ipmt_point_pos)
        self.setup_ipmt_layout.addWidget(self.ipmt_point_button)
        self.ipmt_point_name.textChanged.connect(lambda x: self.update_settings('ipmtpointname', x))
        self.ipmt_point_pos.valueChanged.connect(lambda x: self.update_settings('ipmtpointdepth', x))
        self.ipmt_point_button.pressed.connect(lambda: self.add_simulation({'type':'point', 'parameters':['spoke', {'magnet_depth':self.settings['ipmtpointdepth']}, self.settings['ipmtpointname']]}))

        self.setup_ipmv_widget = QWidget(self)
        self.setup_ipmv_layout = QVBoxLayout()
        self.setup_ipmv_widget.setLayout(self.setup_ipmv_layout)
        self.setup_widget.addTab(self.setup_ipmv_widget, "V-Configuration")

        self.ipmv_sweep_label0 = QLabel("Parameter Sweep Simulation Name:")
        self.ipmv_sweep_name = QLineEdit(self.settings['ipmvsweepname'])
        self.ipmv_range_label1 = QLabel("Magnet Depth:")
        self.ipmv_range_label2 = QLabel("Start:")
        self.ipmv_range_label3 = QLabel("End:")
        self.ipmv_range_label4 = QLabel("Steps:")
        self.ipmv_range_label5 = QLabel("Magnet Angle:")
        self.ipmv_range_label6 = QLabel("Start:")
        self.ipmv_range_label7 = QLabel("End:")
        self.ipmv_range_label8 = QLabel("Steps:")
        self.ipmv_range_layout1 = QHBoxLayout()
        self.ipmv_range_layout2 = QHBoxLayout()
        self.ipmv_range_widget1 = QWidget()
        self.ipmv_range_widget1.setLayout(self.ipmv_range_layout1)
        self.ipmv_range_widget2 = QWidget()
        self.ipmv_range_widget2.setLayout(self.ipmv_range_layout2)
        self.ipmv_range_start1 = QDoubleSpinBox()
        self.ipmv_range_start1.setValue(self.settings['ipmvsweepstart1'])
        self.ipmv_range_end1 = QDoubleSpinBox()
        self.ipmv_range_end1.setValue(self.settings['ipmvsweepend1'])
        self.ipmv_range_step1 = QSpinBox()
        self.ipmv_range_step1.setValue(self.settings['ipmvsweepstep1'])
        self.ipmv_range_start2 = QDoubleSpinBox()
        self.ipmv_range_start2.setValue(self.settings['ipmvsweepstart2'])
        self.ipmv_range_end2 = QDoubleSpinBox()
        self.ipmv_range_end2.setValue(self.settings['ipmvsweepend2'])
        self.ipmv_range_step2 = QSpinBox()
        self.ipmv_range_step2.setValue(self.settings['ipmvsweepstep2'])

        self.setup_ipmv_layout.addWidget(self.ipmv_sweep_label0)
        self.setup_ipmv_layout.addWidget(self.ipmv_sweep_name)

        self.setup_ipmv_layout.addWidget(self.ipmv_range_label1)
        self.setup_ipmv_layout.addWidget(self.ipmv_range_widget1)
        self.ipmv_range_layout1.addWidget(self.ipmv_range_label2)
        self.ipmv_range_layout1.addWidget(self.ipmv_range_start1, 1)
        self.ipmv_range_layout1.addWidget(self.ipmv_range_label3)
        self.ipmv_range_layout1.addWidget(self.ipmv_range_end1, 1)
        self.ipmv_range_layout1.addWidget(self.ipmv_range_label4)
        self.ipmv_range_layout1.addWidget(self.ipmv_range_step1, 1)

        self.setup_ipmv_layout.addWidget(self.ipmv_range_label5)
        self.setup_ipmv_layout.addWidget(self.ipmv_range_widget2)
        self.ipmv_range_layout2.addWidget(self.ipmv_range_label6)
        self.ipmv_range_layout2.addWidget(self.ipmv_range_start2, 1)
        self.ipmv_range_layout2.addWidget(self.ipmv_range_label7)
        self.ipmv_range_layout2.addWidget(self.ipmv_range_end2, 1)
        self.ipmv_range_layout2.addWidget(self.ipmv_range_label8)
        self.ipmv_range_layout2.addWidget(self.ipmv_range_step2, 1)

        self.ipmv_sweep_name.textChanged.connect(lambda x: self.update_settings('ipmvsweepname', x))
        self.ipmv_range_start1.valueChanged.connect(lambda x: self.update_settings('ipmvsweepstart1', x))
        self.ipmv_range_end1.valueChanged.connect(lambda x: self.update_settings('ipmvsweepend1', x))
        self.ipmv_range_step1.valueChanged.connect(lambda x: self.update_settings('ipmvsweepstep1', x))
        self.ipmv_range_start2.valueChanged.connect(lambda x: self.update_settings('ipmvsweepstart2', x))
        self.ipmv_range_end2.valueChanged.connect(lambda x: self.update_settings('ipmvsweepend2', x))
        self.ipmv_range_step2.valueChanged.connect(lambda x: self.update_settings('ipmvsweepstep2', x))

        self.ipmv_sweep_button = QPushButton("Add V-Configuration Sweep to Queue")
        self.ipmv_sweep_button.pressed.connect(lambda: self.add_simulation({'type':'sweep', 'parameters':['vera', {'magnet_depth':[self.settings['ipmvsweepstart1'], self.settings['ipmvsweepend1'], self.settings['ipmvsweepstep1']], 'magnet_angle':[self.settings['ipmvsweepstart2'], self.settings['ipmvsweepend2'], self.settings['ipmvsweepstep2']], 'angle_margin':0}, self.settings['ipmvsweepname']]}))
        self.setup_ipmv_layout.addWidget(self.ipmv_sweep_button)
        
        self.ipmv_point_label0 = QLabel("Single Point Simulation Name:")
        self.ipmv_point_name = QLineEdit(self.settings['ipmvpointname'])
        self.ipmv_point_label1 = QLabel("Magnet Depth:")
        self.ipmv_point_pos1 = QDoubleSpinBox()
        self.ipmv_point_pos1.setValue(self.settings['ipmvpointdepth'])
        self.ipmv_point_label2 = QLabel("Magnet Angle:")
        self.ipmv_point_pos2 = QDoubleSpinBox()
        self.ipmv_point_pos2.setValue(self.settings['ipmvpointangle'])
        self.ipmv_point_button = QPushButton("Add V-Configuration Point Simulation to Queue")
        self.setup_ipmv_layout.addWidget(self.ipmv_point_label0)
        self.setup_ipmv_layout.addWidget(self.ipmv_point_name)
        self.setup_ipmv_layout.addWidget(self.ipmv_point_label1)
        self.setup_ipmv_layout.addWidget(self.ipmv_point_pos1)
        self.setup_ipmv_layout.addWidget(self.ipmv_point_label2)
        self.setup_ipmv_layout.addWidget(self.ipmv_point_pos2)
        self.setup_ipmv_layout.addWidget(self.ipmv_point_button)
        self.ipmv_point_name.textChanged.connect(lambda x: self.update_settings('ipmvpointname', x))
        self.ipmv_point_pos1.valueChanged.connect(lambda x: self.update_settings('ipmvpointdepth', x))
        self.ipmv_point_pos2.valueChanged.connect(lambda x: self.update_settings('ipmvpointangle', x))
        self.ipmv_point_button.pressed.connect(lambda: self.add_simulation({'type':'point', 'parameters':['vera', {'magnet_depth':self.settings['ipmvpointdepth'], 'magnet_angle':self.settings['ipmvpointangle'], 'angle_margin':0}, self.settings['ipmvpointname']]}))

        self.setup_halbach_widget = QWidget(self)
        self.setup_halbach_layout = QVBoxLayout()
        self.setup_halbach_widget.setLayout(self.setup_halbach_layout)
        self.setup_widget.addTab(self.setup_halbach_widget, "Halbach Arrays")

        
        self.halbach_sweep_label0 = QLabel("Parameter Sweep Simulation Name:")
        self.halbach_sweep_name = QLineEdit(self.settings['halbachsweepname'])

        self.halbach_range_label1 = QLabel("Magnet Depth:")
        self.halbach_range_label2 = QLabel("Start:")
        self.halbach_range_label3 = QLabel("End:")
        self.halbach_range_label4 = QLabel("Steps:")

        self.halbach_range_label5 = QLabel("Magnet Ratio:")
        self.halbach_range_label6 = QLabel("Start:")
        self.halbach_range_label7 = QLabel("End:")
        self.halbach_range_label8 = QLabel("Steps:")

        self.halbach_range_label9 = QLabel("Magnet Trapezoid Angle:")
        self.halbach_range_label10 = QLabel("Start:")
        self.halbach_range_label11 = QLabel("End:")
        self.halbach_range_label12 = QLabel("Steps:")

        self.halbach_range_label13 = QLabel("Magnetization Angle:")
        self.halbach_range_label14 = QLabel("Start:")
        self.halbach_range_label15 = QLabel("End:")
        self.halbach_range_label16 = QLabel("Steps:")

        self.halbach_range_layout1 = QHBoxLayout()
        self.halbach_range_layout2 = QHBoxLayout()
        self.halbach_range_layout3 = QHBoxLayout()
        self.halbach_range_layout4 = QHBoxLayout()
        self.halbach_range_widget1 = QWidget()
        self.halbach_range_widget1.setLayout(self.halbach_range_layout1)
        self.halbach_range_widget2 = QWidget()
        self.halbach_range_widget2.setLayout(self.halbach_range_layout2)
        self.halbach_range_widget3 = QWidget()
        self.halbach_range_widget3.setLayout(self.halbach_range_layout3)
        self.halbach_range_widget4 = QWidget()
        self.halbach_range_widget4.setLayout(self.halbach_range_layout4)

        self.halbach_range_start1 = QDoubleSpinBox()
        self.halbach_range_start1.setValue(self.settings['halbachsweepstart1'])
        self.halbach_range_end1 = QDoubleSpinBox()
        self.halbach_range_end1.setValue(self.settings['halbachsweepend1'])
        self.halbach_range_step1 = QSpinBox()
        self.halbach_range_step1.setValue(self.settings['halbachsweepstep1'])
        self.halbach_range_start2 = QDoubleSpinBox()
        self.halbach_range_start2.setValue(self.settings['halbachsweepstart2'])
        self.halbach_range_end2 = QDoubleSpinBox()
        self.halbach_range_end2.setValue(self.settings['halbachsweepend2'])
        self.halbach_range_step2 = QSpinBox()
        self.halbach_range_step2.setValue(self.settings['halbachsweepstep2'])

        self.halbach_sweep_name_layout = QHBoxLayout()
        self.halbach_sweep_name_widget = QWidget()
        self.halbach_sweep_name_widget.setLayout(self.halbach_sweep_name_layout)
        self.halbach_sweep_name_layout.addWidget(self.halbach_sweep_label0)
        self.halbach_sweep_name_layout.addWidget(self.halbach_sweep_name)
        self.setup_halbach_layout.addWidget(self.halbach_sweep_name_widget)

        self.halbach_side_label = QLabel("Use Halbach Side B:")
        self.halbach_side_checkbox = QCheckBox()
        self.halbach_side_widget = QWidget()
        self.halbach_side_layout = QHBoxLayout()
        self.halbach_side_widget.setLayout(self.halbach_side_layout)
        self.halbach_side_layout.addWidget(self.halbach_side_label)
        self.halbach_side_layout.addWidget(self.halbach_side_checkbox, 1)
        self.setup_halbach_layout.addWidget(self.halbach_side_widget)
        self.halbach_side_checkbox.stateChanged.connect(lambda x: self.update_settings('halbachsweepside', 'B' if x == 2 else 'A'))

        self.setup_halbach_layout.addWidget(self.halbach_range_label1)
        self.setup_halbach_layout.addWidget(self.halbach_range_widget1)
        self.halbach_range_layout1.addWidget(self.halbach_range_label2)
        self.halbach_range_layout1.addWidget(self.halbach_range_start1, 1)
        self.halbach_range_layout1.addWidget(self.halbach_range_label3)
        self.halbach_range_layout1.addWidget(self.halbach_range_end1, 1)
        self.halbach_range_layout1.addWidget(self.halbach_range_label4)
        self.halbach_range_layout1.addWidget(self.halbach_range_step1, 1)

        self.setup_halbach_layout.addWidget(self.halbach_range_label5)
        self.setup_halbach_layout.addWidget(self.halbach_range_widget2)
        self.halbach_range_layout2.addWidget(self.halbach_range_label6)
        self.halbach_range_layout2.addWidget(self.halbach_range_start2, 1)
        self.halbach_range_layout2.addWidget(self.halbach_range_label7)
        self.halbach_range_layout2.addWidget(self.halbach_range_end2, 1)
        self.halbach_range_layout2.addWidget(self.halbach_range_label8)
        self.halbach_range_layout2.addWidget(self.halbach_range_step2, 1)

        self.halbach_sweep_name.textChanged.connect(lambda x: self.update_settings('halbachsweepname', x))
        self.halbach_range_start1.valueChanged.connect(lambda x: self.update_settings('halbachsweepstart1', x))
        self.halbach_range_end1.valueChanged.connect(lambda x: self.update_settings('halbachsweepend1', x))
        self.halbach_range_step1.valueChanged.connect(lambda x: self.update_settings('halbachsweepstep1', x))
        self.halbach_range_start2.valueChanged.connect(lambda x: self.update_settings('halbachsweepstart2', x))
        self.halbach_range_end2.valueChanged.connect(lambda x: self.update_settings('halbachsweepend2', x))
        self.halbach_range_step2.valueChanged.connect(lambda x: self.update_settings('halbachsweepstep2', x))
        self.halbach_sweep_button = QPushButton("Add Halbach Sweep to Queue")
        self.halbach_sweep_button.pressed.connect(lambda: self.add_simulation({'type':'sweep', 'parameters':['halbach', {'magnet_depth':[self.settings['halbachsweepstart1'], self.settings['halbachsweepend1'], self.settings['halbachsweepstep1']], 'ratio':[self.settings['halbachsweepstart2'], self.settings['halbachsweepend2'], self.settings['halbachsweepstep2']], 'angle':0, 'magangle':0, 'halbach_side':self.settings['halbachsweepside']}, self.settings['halbachsweepname']]}))
        self.setup_halbach_layout.addWidget(self.halbach_sweep_button)
        
        self.halbach_point_label0 = QLabel("Single Point Simulation Name")
        self.halbach_point_name = QLineEdit(self.settings['halbachpointname'])
        self.halbach_point_label1 = QLabel("Magnet Depth:")
        self.halbach_point_pos1 = QDoubleSpinBox()
        self.halbach_point_pos1.setValue(self.settings['halbachpointdepth'])
        self.halbach_point_label2 = QLabel("Magnet Ratio:")
        self.halbach_point_pos2 = QDoubleSpinBox()
        self.halbach_point_pos2.setValue(self.settings['halbachpointratio'])
        self.halbach_point_button = QPushButton("Add Halbach Point Simulation to Queue")
        self.halbach_point_name_layout = QHBoxLayout()
        self.halbach_point_name_widget = QWidget()
        self.halbach_point_name_widget.setLayout(self.halbach_point_name_layout)
        self.halbach_point_name_layout.addWidget(self.halbach_point_label0)
        self.halbach_point_name_layout.addWidget(self.halbach_point_name)
        self.setup_halbach_layout.addWidget(self.halbach_point_name_widget)

        self.halbach_side_label2 = QLabel("Use Halbach Side B:")
        self.halbach_side_checkbox2 = QCheckBox()
        self.halbach_side_widget2 = QWidget()
        self.halbach_side_layout2 = QHBoxLayout()
        self.halbach_side_widget2.setLayout(self.halbach_side_layout2)
        self.halbach_side_layout2.addWidget(self.halbach_side_label2)
        self.halbach_side_layout2.addWidget(self.halbach_side_checkbox2, 1)
        self.setup_halbach_layout.addWidget(self.halbach_side_widget2)
        self.halbach_side_checkbox2.stateChanged.connect(lambda x: self.update_settings('halbachpointside', 'B' if x == 2 else 'A'))
        
        self.halbach_pos1_layout = QHBoxLayout()
        self.halbach_pos1_widget = QWidget()
        self.halbach_pos1_widget.setLayout(self.halbach_pos1_layout)
        self.halbach_pos1_layout.addWidget(self.halbach_point_label1)
        self.halbach_pos1_layout.addWidget(self.halbach_point_pos1, 1)
        self.setup_halbach_layout.addWidget(self.halbach_pos1_widget)
        
        self.halbach_pos2_layout = QHBoxLayout()
        self.halbach_pos2_widget = QWidget()
        self.halbach_pos2_widget.setLayout(self.halbach_pos2_layout)
        self.halbach_pos2_layout.addWidget(self.halbach_point_label2)
        self.halbach_pos2_layout.addWidget(self.halbach_point_pos2, 1)
        self.setup_halbach_layout.addWidget(self.halbach_pos2_widget)

        self.setup_halbach_layout.addWidget(self.halbach_point_button)

        self.halbach_point_name.textChanged.connect(lambda x: self.update_settings('halbachpointname', x))
        self.halbach_point_pos1.valueChanged.connect(lambda x: self.update_settings('halbachpointdepth', x))
        self.halbach_point_pos2.valueChanged.connect(lambda x: self.update_settings('halbachpointratio', x))
        self.halbach_point_button.pressed.connect(lambda: self.add_simulation({'type':'point', 'parameters':['halbach', {'magnet_depth':self.settings['halbachpointdepth'], 'ratio':self.settings['halbachpointratio'], 'angle':0, 'magangle':0, 'halbach_side':self.settings['halbachpointside']}, self.settings['halbachpointname']]}))

        self.setup_ithma_widget = QWidget(self)
        self.setup_ithma_layout = QVBoxLayout()
        self.setup_ithma_widget.setLayout(self.setup_ithma_layout)
        self.setup_widget.addTab(self.setup_ithma_widget, "ITHMA")

        
        self.ithma_sweep_label0 = QLabel("Parameter Sweep Simulation Name:")
        self.ithma_sweep_name = QLineEdit(self.settings['ithmasweepname'])

        self.ithma_range_label1 = QLabel("Magnet Depth:")

        self.ithma_range_label5 = QLabel("Magnet Ratio:")

        self.ithma_range_label9 = QLabel("Magnet Trapezoid Angle:")
        self.ithma_range_label10 = QLabel("Start:")
        self.ithma_range_label11 = QLabel("End:")
        self.ithma_range_label12 = QLabel("Steps:")

        self.ithma_range_label13 = QLabel("Magnetization Angle:")
        self.ithma_range_label14 = QLabel("Start:")
        self.ithma_range_label15 = QLabel("End:")
        self.ithma_range_label16 = QLabel("Steps:")

        self.ithma_range_layout1 = QHBoxLayout()
        self.ithma_range_layout2 = QHBoxLayout()
        self.ithma_range_layout3 = QHBoxLayout()
        self.ithma_range_layout4 = QHBoxLayout()
        self.ithma_range_widget1 = QWidget()
        self.ithma_range_widget1.setLayout(self.ithma_range_layout1)
        self.ithma_range_widget2 = QWidget()
        self.ithma_range_widget2.setLayout(self.ithma_range_layout2)
        self.ithma_range_widget3 = QWidget()
        self.ithma_range_widget3.setLayout(self.ithma_range_layout3)
        self.ithma_range_widget4 = QWidget()
        self.ithma_range_widget4.setLayout(self.ithma_range_layout4)

        self.ithma_depth = QDoubleSpinBox()
        self.ithma_depth.setValue(self.settings['ithmasweepdepth'])
        self.ithma_range_layout1.addWidget(self.ithma_range_label1)
        self.ithma_range_layout1.addWidget(self.ithma_depth, 1)

        
        self.ithma_ratio = QDoubleSpinBox()
        self.ithma_ratio.setValue(self.settings['ithmasweepratio'])
        self.ithma_range_layout2.addWidget(self.ithma_range_label5)
        self.ithma_range_layout2.addWidget(self.ithma_ratio, 1)

        self.ithma_range_start3 = QDoubleSpinBox()
        self.ithma_range_start3.setValue(self.settings['ithmasweepstart3'])
        self.ithma_range_end3 = QDoubleSpinBox()
        self.ithma_range_end3.setValue(self.settings['ithmasweepend3'])
        self.ithma_range_step3 = QSpinBox()
        self.ithma_range_step3.setValue(self.settings['ithmasweepstep3'])
        self.ithma_range_start4 = QDoubleSpinBox()
        self.ithma_range_start4.setValue(self.settings['ithmasweepstart4'])
        self.ithma_range_end4 = QDoubleSpinBox()
        self.ithma_range_end4.setValue(self.settings['ithmasweepend4'])
        self.ithma_range_step4 = QSpinBox()
        self.ithma_range_step4.setValue(self.settings['ithmasweepstep4'])

        self.ithma_sweep_name_layout = QHBoxLayout()
        self.ithma_sweep_name_widget = QWidget()
        self.ithma_sweep_name_widget.setLayout(self.ithma_sweep_name_layout)
        self.ithma_sweep_name_layout.addWidget(self.ithma_sweep_label0)
        self.ithma_sweep_name_layout.addWidget(self.ithma_sweep_name)
        self.setup_ithma_layout.addWidget(self.ithma_sweep_name_widget)

        self.ithma_side_label = QLabel("Use ITHMA Side B:")
        self.ithma_side_checkbox = QCheckBox()
        self.ithma_side_widget = QWidget()
        self.ithma_side_layout = QHBoxLayout()
        self.ithma_side_widget.setLayout(self.ithma_side_layout)
        self.ithma_side_layout.addWidget(self.ithma_side_label)
        self.ithma_side_layout.addWidget(self.ithma_side_checkbox, 1)
        self.setup_ithma_layout.addWidget(self.ithma_side_widget)
        self.ithma_side_checkbox.stateChanged.connect(lambda x: self.update_settings('ithmasweepside', 'B' if x == 2 else 'A'))

        self.setup_ithma_layout.addWidget(self.ithma_range_widget1)
        self.setup_ithma_layout.addWidget(self.ithma_range_widget2)

        self.setup_ithma_layout.addWidget(self.ithma_range_label9)
        self.setup_ithma_layout.addWidget(self.ithma_range_widget3)
        self.ithma_range_layout3.addWidget(self.ithma_range_label10)
        self.ithma_range_layout3.addWidget(self.ithma_range_start3, 1)
        self.ithma_range_layout3.addWidget(self.ithma_range_label11)
        self.ithma_range_layout3.addWidget(self.ithma_range_end3, 1)
        self.ithma_range_layout3.addWidget(self.ithma_range_label12)
        self.ithma_range_layout3.addWidget(self.ithma_range_step3, 1)

        self.setup_ithma_layout.addWidget(self.ithma_range_label13)
        self.setup_ithma_layout.addWidget(self.ithma_range_widget4)
        self.ithma_range_layout4.addWidget(self.ithma_range_label14)
        self.ithma_range_layout4.addWidget(self.ithma_range_start4, 1)
        self.ithma_range_layout4.addWidget(self.ithma_range_label15)
        self.ithma_range_layout4.addWidget(self.ithma_range_end4, 1)
        self.ithma_range_layout4.addWidget(self.ithma_range_label16)
        self.ithma_range_layout4.addWidget(self.ithma_range_step4, 1)

        self.ithma_sweep_name.textChanged.connect(lambda x: self.update_settings('ithmasweepname', x))
        self.ithma_depth.valueChanged.connect(lambda x: self.update_settings('ithmasweepdepth', x))
        self.ithma_ratio.valueChanged.connect(lambda x: self.update_settings('ithmasweepratio', x))
        self.ithma_range_start3.valueChanged.connect(lambda x: self.update_settings('ithmasweepstart3', x))
        self.ithma_range_end3.valueChanged.connect(lambda x: self.update_settings('ithmasweepend3', x))
        self.ithma_range_step3.valueChanged.connect(lambda x: self.update_settings('ithmasweepstep3', x))
        self.ithma_range_start4.valueChanged.connect(lambda x: self.update_settings('ithmasweepstart4', x))
        self.ithma_range_end4.valueChanged.connect(lambda x: self.update_settings('ithmasweepend4', x))
        self.ithma_range_step4.valueChanged.connect(lambda x: self.update_settings('ithmasweepstep4', x))
        self.ithma_sweep_button = QPushButton("Add ITHMA Sweep to Queue")
        self.ithma_sweep_button.pressed.connect(lambda: self.add_simulation({'type':'sweep', 'parameters':['halbach', {'magnet_depth':self.settings['ithmasweepdepth'], 'ratio':self.settings['ithmasweepratio'], 'angle':[self.settings['ithmasweepstart3'], self.settings['ithmasweepend3'], self.settings['ithmasweepstep3']], 'magangle':[self.settings['ithmasweepstart4'], self.settings['ithmasweepend4'], self.settings['ithmasweepstep4']], 'ithma_side':self.settings['ithmasweepside']}, self.settings['ithmasweepname']]}))
        self.setup_ithma_layout.addWidget(self.ithma_sweep_button)
        
        self.ithma_point_label0 = QLabel("Single Point Simulation Name")
        self.ithma_point_name = QLineEdit(self.settings['ithmapointname'])
        self.ithma_point_label1 = QLabel("Magnet Depth:")
        self.ithma_point_pos1 = QDoubleSpinBox()
        self.ithma_point_pos1.setValue(self.settings['ithmapointdepth'])
        self.ithma_point_label2 = QLabel("Magnet Ratio:")
        self.ithma_point_pos2 = QDoubleSpinBox()
        self.ithma_point_pos2.setValue(self.settings['ithmapointratio'])
        self.ithma_point_label3 = QLabel("Magnet Trapezoid Angle:")
        self.ithma_point_pos3 = QDoubleSpinBox()
        self.ithma_point_pos3.setValue(self.settings['ithmapointangle'])
        self.ithma_point_label4 = QLabel("Magnetization Angle:")
        self.ithma_point_pos4 = QDoubleSpinBox()
        self.ithma_point_pos4.setValue(self.settings['ithmapointmagangle'])
        self.ithma_point_button = QPushButton("Add ITHMA Point Simulation to Queue")
        self.ithma_point_name_layout = QHBoxLayout()
        self.ithma_point_name_widget = QWidget()
        self.ithma_point_name_widget.setLayout(self.ithma_point_name_layout)
        self.ithma_point_name_layout.addWidget(self.ithma_point_label0)
        self.ithma_point_name_layout.addWidget(self.ithma_point_name)
        self.setup_ithma_layout.addWidget(self.ithma_point_name_widget)

        self.ithma_side_label2 = QLabel("Use ITHMA Side B:")
        self.ithma_side_checkbox2 = QCheckBox()
        self.ithma_side_widget2 = QWidget()
        self.ithma_side_layout2 = QHBoxLayout()
        self.ithma_side_widget2.setLayout(self.ithma_side_layout2)
        self.ithma_side_layout2.addWidget(self.ithma_side_label2)
        self.ithma_side_layout2.addWidget(self.ithma_side_checkbox2, 1)
        self.setup_ithma_layout.addWidget(self.ithma_side_widget2)
        self.ithma_side_checkbox2.stateChanged.connect(lambda x: self.update_settings('ithmapointside', 'B' if x == 2 else 'A'))
        
        self.ithma_pos1_layout = QHBoxLayout()
        self.ithma_pos1_widget = QWidget()
        self.ithma_pos1_widget.setLayout(self.ithma_pos1_layout)
        self.ithma_pos1_layout.addWidget(self.ithma_point_label1)
        self.ithma_pos1_layout.addWidget(self.ithma_point_pos1, 1)
        self.setup_ithma_layout.addWidget(self.ithma_pos1_widget)
        
        self.ithma_pos2_layout = QHBoxLayout()
        self.ithma_pos2_widget = QWidget()
        self.ithma_pos2_widget.setLayout(self.ithma_pos2_layout)
        self.ithma_pos2_layout.addWidget(self.ithma_point_label2)
        self.ithma_pos2_layout.addWidget(self.ithma_point_pos2, 1)
        self.setup_ithma_layout.addWidget(self.ithma_pos2_widget)
        
        self.ithma_pos3_layout = QHBoxLayout()
        self.ithma_pos3_widget = QWidget()
        self.ithma_pos3_widget.setLayout(self.ithma_pos3_layout)
        self.ithma_pos3_layout.addWidget(self.ithma_point_label3)
        self.ithma_pos3_layout.addWidget(self.ithma_point_pos3, 1)
        self.setup_ithma_layout.addWidget(self.ithma_pos3_widget)
        
        self.ithma_pos4_layout = QHBoxLayout()
        self.ithma_pos4_widget = QWidget()
        self.ithma_pos4_widget.setLayout(self.ithma_pos4_layout)
        self.ithma_pos4_layout.addWidget(self.ithma_point_label4)
        self.ithma_pos4_layout.addWidget(self.ithma_point_pos4, 1)
        self.setup_ithma_layout.addWidget(self.ithma_pos4_widget)
        self.setup_ithma_layout.addWidget(self.ithma_point_button)

        self.ithma_point_name.textChanged.connect(lambda x: self.update_settings('ithmapointname', x))
        self.ithma_point_pos1.valueChanged.connect(lambda x: self.update_settings('ithmapointdepth', x))
        self.ithma_point_pos2.valueChanged.connect(lambda x: self.update_settings('ithmapointratio', x))
        self.ithma_point_pos3.valueChanged.connect(lambda x: self.update_settings('ithmapointangle', x))
        self.ithma_point_pos4.valueChanged.connect(lambda x: self.update_settings('ithmapointmagangle', x))
        self.ithma_point_button.pressed.connect(lambda: self.add_simulation({'type':'point', 'parameters':['halbach', {'magnet_depth':self.settings['ithmapointdepth'], 'ratio':self.settings['ithmapointratio'], 'angle':self.settings['ithmapointangle'], 'magangle':self.settings['ithmapointmagangle'], 'ithma_side':self.settings['ithmapointside']}, self.settings['ithmapointname']]}))

        self.main_content_widget = QWidget()
        self.hlayout.addWidget(self.main_content_widget)

        self.sim_select_widget = QWidget()
        self.sim_select_layout = QVBoxLayout()
        self.sim_select_widget.setLayout(self.sim_select_layout)
        self.hlayout.addWidget(self.sim_select_widget)

        self.sim_select_label1 = QLabel("Available Simulations:")
        self.sim_select_layout.addWidget(self.sim_select_label1)

        self.sim_select_list = QListWidget()
        for sim in self.settings['simulations']:
            self.sim_select_list.addItem(sim['parameters'][2])
        self.sim_select_list.setCurrentRow(0)
        self.sim_select_layout.addWidget(self.sim_select_list)

        self.simulate_buttons_widget = QWidget()
        self.simulate_buttons_layout = QHBoxLayout()
        self.simulate_buttons_widget.setLayout(self.simulate_buttons_layout)
        self.simulate_one_button = QPushButton("Simulate Selected")
        self.simulate_all_button = QPushButton("Simulate All")
        self.simulate_delete_button = QPushButton("Delete Selected")
        self.simulate_buttons_layout.addWidget(self.simulate_one_button)
        self.simulate_buttons_layout.addWidget(self.simulate_all_button)
        self.simulate_buttons_layout.addWidget(self.simulate_delete_button)
        self.simulate_one_button.pressed.connect(self.simulate_current)
        self.simulate_all_button.pressed.connect(self.simulate_all)
        self.simulate_delete_button.pressed.connect(self.delete_current_simulation)
        self.sim_select_layout.addWidget(self.simulate_buttons_widget)
    
        self.sim_select_label2 = QLabel("Finished Simulations:")
        self.sim_select_layout.addWidget(self.sim_select_label2)

        self.sim_show_widget = QTreeWidget()
        self.sim_show_widget.setHeaderHidden(True)
        self.sim_select_layout.addWidget(self.sim_show_widget)
        self.sim_show_widget.itemClicked.connect(self.tree_item_click)

        self.sim_show_delete_button = QPushButton('Delete Selected Plot')
        self.sim_show_delete_button.pressed.connect(self.delete_current_plot)
        self.sim_select_layout.addWidget(self.sim_show_delete_button)

    def update_plot(self, new_widget):
        self.hlayout.replaceWidget(self.hlayout.indexOf(self.main_content_widget), new_widget)
        self.main_content_widget = new_widget    

    def update_results(self):
        self.sim_show_widget.clear()
        for i in range(len(self.results)):
            simulation_item = QTreeWidgetItem([self.results[i]['name']])
            # simulation_item.setData(0, 1, i)
            self.sim_show_widget.addTopLevelItem(simulation_item)
            for index in range(len(self.results[i]['sims'])):
                item = QTreeWidgetItem([self.results[i]['sims'][index][0]])
                simulation_item.addChild(item)
                item.setData(0, 1, [i, index])

    def tree_item_click(self, item):
        widget = item.data(0, 1)
        if widget is not None:
            self.update_plot(self.results[widget[0]]['sims'][widget[1]][1])
    
    def delete_current_plot(self):
        selected_item = self.sim_show_widget.currentItem()
        if selected_item:
            # If selected item is a group, delete the whole group
            parent = selected_item.parent()
            if parent is None:
                # Root level item
                index = self.sim_show_widget.indexOfTopLevelItem(selected_item)
                self.results.pop(index)
                self.sim_show_widget.takeTopLevelItem(index)
            else:
                self.results
                widget = selected_item.data(0, 1)
                if widget is not None:
                    self.results[widget[0]]['sims'][widget[1]][1].close()
                index = parent.indexOfChild(selected_item)
                parent.takeChild(index)
            self.update_plot(QWidget())

    def delete_current_simulation(self):
        if len(self.settings['simulations']) == 0:
            self.parent.statusBar.showMessage("Add Simulations to Queue first.")
            return
        i = self.sim_select_list.currentRow()
        self.sim_select_list.takeItem(i)
        self.settings['simulations'].pop(i)
        self.settings.save()
        self.update_sim_queue()

    def run_simulation(self, index):
        self.parent.setEnabled(False)
        simulation = self.settings['simulations'][index].copy()
        simulation['parameters'][1].update({'stator_path':self.settings['stator_path']})
        simpars = simulation['parameters'][1:]
        simpars[0].update(self.settings.data)
        if simulation['type'] == "sweep":
            if simulation['parameters'][0] == "initial":
                figs = sweep_1d(initial, *simpars, path=self.tmp_project_path)
            elif simulation['parameters'][0] == "burried":
                figs = sweep_1d(burried, *simpars, path=self.tmp_project_path)
            elif simulation['parameters'][0] == "spoke":
                figs = sweep_1d(spoke, *simpars, path=self.tmp_project_path)
            elif simulation['parameters'][0] == "vera":
                figs = sweep_2d(vera, *simpars, "Magnet Angle in Degrees", path=self.tmp_project_path)
            elif simulation['parameters'][0] == "halbach":
                if isinstance(simulation['parameters'][1]['magnet_depth'], list):
                    figs = sweep_2d(halbach, *simpars, "Magnet Factor", path=self.tmp_project_path)
                else:
                    figs = sweep_2d(halbach, *simpars, 'Magnetization Direction in Degrees', xlabel="Trapezoidal Angle in Degrees", path=self.tmp_project_path)
        else:
            if simulation['parameters'][0] == "initial":
                figs = simulate_everything(initial, *simpars, path=self.tmp_project_path)
            elif simulation['parameters'][0] == "burried":
                figs = simulate_everything(burried, *simpars, path=self.tmp_project_path)
            elif simulation['parameters'][0] == "spoke":
                figs = simulate_everything(spoke, *simpars, path=self.tmp_project_path)
            elif simulation['parameters'][0] == "vera":
                figs = simulate_everything(vera, *simpars, path=self.tmp_project_path)
            elif simulation['parameters'][0] == "halbach":
                figs = simulate_everything(halbach, *simpars, path=self.tmp_project_path)
        self.results.append({'name':simulation['parameters'][2],
                                         'sims': [[str(key), MatplotlibWidget(val)] for key, val in figs.items()]})
        self.update_results()
        self.parent.setEnabled(True)

    def simulate_current(self):
        if len(self.settings['simulations']) == 0:
            self.parent.statusBar.showMessage("Add Simulations to Queue first.")
            return
        i = self.sim_select_list.currentRow()
        self.run_simulation(i)
    
    def simulate_all(self):
        if len(self.settings['simulations']) == 0:
            self.parent.statusBar.showMessage("Add Simulations to Queue first.")
            return
        for i in range(len(self.settings['simulations'])):
            self.run_simulation(i)

    def update_sim_queue(self):
        self.sim_select_list.clear()
        for sim in self.settings['simulations']:
            self.sim_select_list.addItem(sim['parameters'][2])
        self.sim_select_list.setCurrentRow(len(self.settings['simulations'])-1)

    def add_simulation(self, dict):
        if self.settings['stator_path'] == '':
            self.parent.statusBar.showMessage("Select a Stator File first.")
            return
        self.settings['simulations'].append(dict)
        self.settings.save()
        self.update_sim_queue()

    def setup_general_fname_select(self):
        filename, _ = QFileDialog.getOpenFileName(
                self, "Select the stator file", "", "FEM Files (*.fem)"
            )
        if not filename:
            return 1
        self.settings['stator_path'] = filename
        shutil.copyfile(filename, os.path.join(self.tmp_project_path, 'stator.FEM'))
        self.setup_general_fname_label.setText(f"Stator file: {filename}")
        self.save_required = True
        return 0
    
    def update_settings(self, key, value):
        self.settings[key] = value
        
    def save(self):
        if self.save_path == None:
            res = self.saveas()
        else:
            file_handler = PMSMFileHandler(self.tmp_project_path)
            file_handler.pack(self.save_path)
            res = 0
        if res == 0:
            self.save_required = False
        return res
    
    def saveas(self, filename=None):
        if filename == None:
            filename, ok = QFileDialog.getSaveFileName(self, f"Select location to save {self.settings['project_name']} to", "", "PMSM Files (*.pmsm);;All Files (*)")
        if ok:
            self.settings['project_name'] = os.path.basename(filename).split('.')[0]
            self.save_path = filename
            self.parent.rename_project(name=self.settings['project_name'])
            file_handler = PMSMFileHandler(self.tmp_project_path)
            file_handler.pack(filename)
            self.save_required = False
            return 0
        else:
            return 1

    def close(self):
        return
    
    def get_name(self):
        return self.settings['project_name']

class MainWindow(QMainWindow):
    def __init__(self):
        global default_application_settings
        super().__init__()

        self.file_list = []

        self.settings = SettingsManager('settings.json', initial_settings=default_application_settings)

        self.setWindowTitle("SM Rotor Geometry Configurator")
        self.setGeometry(self.settings['window_position_x'], self.settings['window_position_y'], self.settings['window_width'], self.settings['window_height'])

        self.main_widget = QTabWidget(self)
        self.main_widget.setTabPosition(QTabWidget.TabPosition.North) 
        self.setCentralWidget(self.main_widget) 
        self.main_widget.setMovable(True) 
        self.main_widget.setTabsClosable(True)
        self.main_widget.tabCloseRequested.connect(self.close_project) 

        self.new_file_action = QAction('Create New Project', self)
        self.new_file_action.setStatusTip("Create a new project") 
        self.new_file_action.triggered.connect(self.new_project) 
        self.new_file_action.setShortcut("Ctrl+n")
        
        self.open_file_action = QAction('Open Project', self)
        self.open_file_action.setStatusTip("Open an existing project") 
        self.open_file_action.triggered.connect(self.open_project) 
        self.open_file_action.setShortcut("Ctrl+o") 

        self.save_file_action = QAction('Save Project', self)
        self.save_file_action.setStatusTip("Save the current project") 
        self.save_file_action.triggered.connect(self.request_save_project) 
        self.save_file_action.setShortcut("Ctrl+s") 

        self.saveas_file_action = QAction('Save Project as', self)
        self.saveas_file_action.setStatusTip("Save the current project as a different file") 
        self.saveas_file_action.triggered.connect(self.request_saveas_project) 
        self.saveas_file_action.setShortcut("Ctrl+Shift+s")

        self.close_file_action = QAction('Close Project', self)
        self.close_file_action.setStatusTip("Close the project that's shown right now") 
        self.close_file_action.triggered.connect(self.close_project) 
        self.close_file_action.setShortcut("Ctrl+t") 

        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("&Project")
        self.file_menu.addAction(self.new_file_action)
        self.file_menu.addAction(self.open_file_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.close_file_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.save_file_action)
        self.file_menu.addAction(self.saveas_file_action)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        if os.path.exists('tmp'):
            shutil.rmtree('tmp')
        os.makedirs('tmp')

        self.open_project(os.path.join('examples', 'ba-laurin-weitzel.pmsm'))
        self.statusBar.showMessage("Welcome to the PMSM Rotor Geometry Analyzer")


    def new_project(self):
        global new_project_index
        project_name = f"New Project {new_project_index}"
        new_widget = FileWidget(self, name=project_name)
        self.file_list.append(new_widget)
        self.main_widget.addTab(new_widget, project_name)
        new_project_index += 1
        return new_widget
    
    def open_project(self, path=None):
        if path == None:
            filename, _ = QFileDialog.getOpenFileName(
                    self, "Select the project to open", "", "PMSM Files (*.pmsm);;All Files (*)"
                )
        else:
            filename = path
        if not filename:
            return None
        new_widget = FileWidget(self, path=filename)
        self.file_list.append(new_widget)
        self.main_widget.addTab(new_widget, new_widget.get_name())
        return new_widget
    
    def close_project(self, index=None):
        if index is None:
            active_widget = self.main_widget.currentWidget()
        else:
            active_widget = self.main_widget.widget(index)
        try:
            active_widget.close()
        except AttributeError:
            return 1
        active_widget_index = self.main_widget.indexOf(active_widget)
        self.file_list.pop(active_widget_index)
        self.main_widget.removeTab(active_widget_index)
        return 0
    
    def rename_project(self, name=None, index=None):
        if index is None:
            active_widget = self.main_widget.currentWidget()
        else:
            active_widget = self.main_widget.widget(index)
        if name is None:
            text, ok = QInputDialog.getText(self, 'Rename Project', 'Enter new project name:')
            if ok:
                name = text
            active_widget.rename(name)
        self.main_widget.setTabText(self.main_widget.currentIndex(), name)
    
    def request_save_project(self, index=None):
        if index is None:
            active_widget = self.main_widget.currentWidget()
        else:
            active_widget = self.main_widget.widget(index)
        try:
            res = active_widget.save()
            if res == 0:
                self.statusBar.showMessage("Project was saved successfully")
            else:
                self.statusBar.showMessage("There has been an error saving the project")
        except AttributeError:
            return 1
        return 0
    
    def request_saveas_project(self, index=None):
        if index is None:
            active_widget = self.main_widget.currentWidget()
        else:
            active_widget = self.main_widget.widget(index)
        try:
            res = active_widget.saveas()
            if res == 0:
                self.statusBar.showMessage("Project was saved successfully")
            else:
                self.statusBar.showMessage("There has been an error saving the project")
        except AttributeError:
            return 1
        return 0
    
    def closeEvent(self, a0: QCloseEvent | None) -> None:
        window_geometry = self.geometry()
        self.settings['window_width'] = window_geometry.width()
        self.settings['window_height'] = window_geometry.height()
        self.settings['window_position_x'] = window_geometry.x()
        self.settings['window_position_y'] = window_geometry.y()
        return super().closeEvent(a0)

if __name__=="__main__":
    app = QApplication(sys.argv)
    #qd.setup_theme(theme='light', custom_colors={"primary": "#C7105C"}, corner_shape="sharp")
    window = MainWindow()
    window.show()
    app.exec()
