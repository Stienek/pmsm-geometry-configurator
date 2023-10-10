import sys, os, shutil
import json
import zlib

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

import qdarktheme as qd

default_application_settings = {
    'window_width': 800,
    'window_height': 600,
    'window_position_x': 100,
    'window_position_y': 100,
    'last_project': None,
    'show_welcome_message': True,
}

new_project_index = 0

os.chdir(os.path.dirname(sys.argv[0]))

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

    def update(self, new_data):
        self.data.update(new_data)
        self.save()

    def __repr__(self):
        return repr(self.data)
    
    def save(self):
        with open(self.file_path, 'w') as file:
            json.dump(self.data, file)



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


class FileWidget(QSplitter):
    def __init__(self, parent, name=None, path=None):
        super().__init__(parent)
        
        if path == None:
            if name == None:
                raise AttributeError("FileWidget either needs a name or a path to a project.")
            self.tmp_project_path = os.path.join('tmp', name)
            os.mkdir(self.tmp_project_path)
            
            
        else:
            if not os.path.exists(path):
                raise FileNotFoundError("The specified project does not exist.")
            self.tmp_project_path = os.path.basename(path).split('.')[0]
            
        self.settings = SettingsManager(os.path.join(self.tmp_project_path, "settings.json"), initial_settings={'project_name':name})

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.hlayout = QSplitter(Qt.Orientation.Horizontal)
        self.addWidget(self.hlayout)

        # self.hlayout.addWidget(self.tree_widget)

        self.hlayout.setStretchFactor(0, 1)
        self.hlayout.setStretchFactor(1, 2)
        self.hlayout.setStretchFactor(2, 1)

        self.hlayout.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

    def close(self):
        return

class MainWindow(QMainWindow):
    def __init__(self):
        global default_application_settings
        super().__init__()

        self.file_list = []

        self.settings = SettingsManager('settings.json', initial_settings=default_application_settings)

        self.setWindowTitle("SM Rotor Geometry Configurator")
        self.setGeometry(self.settings['window_position_x'], self.settings['window_position_y'], self.settings['window_width'], self.settings['window_height'])

        self.main_widget = QTabWidget(self)
        self.main_widget.setTabPosition(QTabWidget.TabPosition.West) 
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

        self.close_file_action = QAction('Close Project', self)
        self.close_file_action.setStatusTip("Close the project that's shown right now") 
        self.close_file_action.triggered.connect(self.close_project) 
        self.close_file_action.setShortcut("Ctrl+t") 

        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("&File")
        self.file_menu.addAction(self.new_file_action)
        self.file_menu.addAction(self.open_file_action)
        self.file_menu.addAction(self.close_file_action)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        if os.path.exists('tmp'):
            shutil.rmtree('tmp')
        os.makedirs('tmp')

        if self.settings['last_project'] is not None:
            self.open_project(self.settings['last_project'])
        else:
            self.new_project()
        self.statusBar.showMessage("Welcome to the PMSM Rotor Geometry Analyzer")


    def new_project(self):
        global new_project_index
        project_name = f"New Project {new_project_index}"
        new_widget = FileWidget(self, name=project_name)
        self.file_list.append(new_widget)
        self.main_widget.addTab(new_widget, project_name)
        new_project_index += 1
        return new_widget
    
    def open_project(self, project_name=None):
        if project_name is None:
            filename, _ = QFileDialog.getOpenFileName(
                    self, "Select the project to open", "", "PMSM Files (*.pmsm);;All Files (*)"
                )
            if not filename:
                return None
        else:
            filename = project_name
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
    
    def request_save_project(self, index=None):
        if index is None:
            active_widget = self.main_widget.currentWidget()
        else:
            active_widget = self.main_widget.widget(index)
        try:
            active_widget.save()
        except AttributeError:
            return 1
        self.statusBar.showMessage("Project was saved successfully")
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
    qd.setup_theme(custom_colors={"primary": "#C7105C"}, corner_shape="sharp")
    window = MainWindow()
    window.show()
    app.exec()
