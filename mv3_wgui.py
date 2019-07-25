import os
import sys
import time
import traceback
from pathlib import Path
from os.path import isfile, join

#external packages
import cv2
import tqdm
import imageio
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui, uic

class Worker(QtCore.QObject):
    '''
    Worker thread that handles the major program load. Allowing the gui to still be responsive.
    '''
    def __init__(self, filenames, config):
        super(Worker, self).__init__()
        self.filenames = filenames
        self.config = config

    progress = QtCore.pyqtSignal(float)
    call_video = QtCore.pyqtSignal()
    call_images = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()

    @QtCore.pyqtSlot()
    def run(self, some_string_arg):
        self.function(*self.args, **self.kwargs)

    @QtCore.pyqtSlot()
    def images(self):
        cap = cv2.VideoCapture(self.filenames)
        length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(5)
        print("video fps:", fps)
        skipframes = 0  #int(fps)
        print(skipframes)
        print("number of frames:", length)
        width = len(str(length))
        dir = "\\".join(Path(self.filenames).parts[:-1])+"\\"+(str(Path(self.filenames).parts[-1]).split(".")[0]+"_images")
        print("creates folder:", dir)
        try:
            os.mkdir(dir)
        except FileExistsError:
            print("folder exists!")
            return
        else:
            ret = True
            i = 1
            while ret:
                filename = str(i).rjust(width,"0")+'.png'
                for _ in range(skipframes+1):
                    ret, frame = cap.read()
                #print(ret)
                if ret:
                    cv2.imwrite(dir+"\\"+filename, frame)
                    print("saves", dir+"\\"+filename)
                    self.progress.emit(100 * ((i*(skipframes+1)) / length))
                    i += 1
            self.finished.emit()
        finally:
            cap.release()

    @QtCore.pyqtSlot()
    def video(self):
        #### PARAMETERS
        container = ".mp4" #".avi" #
        codec = "HEVC" #"DIVX" #
        if self.config["max_length"] > 0:
            max_length = min(self.config["max_length"], len(self.filenames))
        else:
            max_length = len(self.filenames)
        size = self.config["size"]
        repeatframe = self.config["repeatframe"]
        fps = self.config["fps"]

        self.filenames = self.filenames[:max_length]
        name = "video_" + time.strftime("%y_%m_%d_%H-%M-%S", time.localtime()) + container
        output_path = "videos/" + name

        if size[0] == 0 and size[1] == 0:
            tframe = cv2.imread(self.filenames[0])
            (oldh, oldw, depth) = tframe.shape
            size = (oldw, oldh)
            print(tframe.shape)
        print("SIZE")
        print(size)
        output = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*codec), fps, size)

        length = len(self.filenames)
        for idx, file in tqdm.tqdm(enumerate(self.filenames)):
            frame = cv2.imread(file)
            #resizing
            (oldh, oldw, depth) = frame.shape
            print(frame.shape)
            woffset = (oldw - size[0]) // 2
            hoffset = (oldh - size[1]) // 2
            print(woffset)
            print(hoffset)
            frame = frame[hoffset:hoffset + size[1], woffset:woffset + size[0]]
            print("goes 1")
            for i in range(repeatframe):
                print("goes 2")
                output.write(frame)
                print(frame.shape)
            self.progress.emit(100 * ((idx + 1) / length))
        output.release()
        print("Saved Video in", output_path)
        print("Number of frames:", len(self.filenames) * repeatframe)
        self.finished.emit()

class HelloWindow(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.setMinimumSize(QtCore.QSize(440, 180))
        uic.loadUi("mv3_gui.ui",self)
        self.setWindowTitle("Videomaker")

        self.mv_button.setEnabled(False)
        self.config = {
            "max_length": 600,
            "size": (0, 0),
            "repeatframe": 10,
            "fps": 10,
        }
        self.mode = "f2v"
        self.progress.setValue(0)
        self.set_defaults()
        self.update_config()
        self.change_mode(0)
        self.setup_connections()

    def setup_connections(self):
        self.data_button.clicked.connect(self.filedialog_folder)
        self.mv_button.clicked.connect(self.action)

        self.max_length_le.textChanged.connect(self.update_config)
        self.size1_le.textChanged.connect(self.update_config)
        self.size2_le.textChanged.connect(self.update_config)
        self.repeatframe_le.textChanged.connect(self.update_config)
        self.fps_le.textChanged.connect(self.update_config)
        self.mode_slider.valueChanged.connect(self.change_mode)

    @QtCore.pyqtSlot(float)
    def on_progress(self, value):
        self.progress.setValue(value)

    @QtCore.pyqtSlot()
    def on_finish(self):
        self.data_button.setEnabled(True)
        self.mode_slider.setEnabled(True)
        self.my_thread.quit()

    def filedialog_folder(self):
        """
        Opens an os native file dialog and returns a list of all selected files.
        Sets the list of selected files as content to the line edit.
        """
        self.progress.setValue(0)
        dlg = QtWidgets.QFileDialog()
        if self.mode == "f2v":
            folder = dlg.getExistingDirectory(self, 'Select video folder', os.getcwd())
            self.data_label.setText(folder)
            try:
                print("Loading data...")
                files = os.listdir(folder)
            except FileNotFoundError:
                print("...no data.")
                return
            files.sort()
            #max_length = min(self.config["max_length"], len(files))
            #files = files[:max_length]
            self.filenames = [join(folder, f) for f in files]
            print(self.filenames)
            print("length", len( self.filenames))
            print("=================\nfinished loading files from folder")
            self.mv_button.setEnabled(True)
        if self.mode == "v2f":
            video_file, _ = dlg.getOpenFileNames(self, 'Select video file', os.getcwd())
            if not video_file:
                return
            self.data_label.setText(video_file[0])
            if not any([type in video_file[0] for type in [".avi", ".mp4"]]):
                print("...no data.")
                return
            else:
                self.filenames = video_file[0]
                print(self.filenames)
                print("=================\nfinished loading video")
                self.mv_button.setEnabled(True)

    def action(self):
        self.mv_button.setEnabled(False)
        self.data_button.setEnabled(False)
        self.mode_slider.setEnabled(False)
        self.my_thread = QtCore.QThread()
        self.my_thread.start()
        if self.mode == "f2v":
            self.save_movie()
        if self.mode == "v2f":
            self.make_images()

    def make_images(self):
        self.my_worker = Worker(self.filenames, None)
        self.my_worker.moveToThread(self.my_thread)
        self.my_worker.call_images.connect(self.my_worker.images)
        self.my_worker.progress.connect(self.on_progress)
        self.my_worker.finished.connect(self.on_finish)
        self.my_worker.call_images.emit()

    def save_movie(self):
        self.my_worker = Worker(self.filenames, self.config)
        self.my_worker.moveToThread(self.my_thread)
        self.my_worker.call_video.connect(self.my_worker.video)
        self.my_worker.progress.connect(self.on_progress)
        self.my_worker.finished.connect(self.on_finish)
        self.my_worker.call_video.emit()

    @QtCore.pyqtSlot(int)
    def change_mode(self, value):
        self.progress.setValue(0)
        self.filenames = []
        self.mv_button.setEnabled(False)
        if value == 0:
            self.mode = "f2v"
            self.data_label.setText("select a folder that contains the images")
            self.data_button.setText("select folder")
            self.mv_button.setText("make video")
            self.config_widget.show()
        if value == 1:
            self.mode = "v2f"
            self.data_label.setText("select the video file")
            self.data_button.setText("select video")
            self.mv_button.setText("make image folder")
            self.config_widget.hide()

    def set_defaults(self):
        self.max_length_le.setText(str(self.config["max_length"]))
        self.size1_le.setText(str(self.config["size"][0]))
        self.size2_le.setText(str(self.config["size"][1]))
        self.repeatframe_le.setText(str(self.config["repeatframe"]))
        self.fps_le.setText(str(self.config["fps"]))


    def update_config(self):
        try:
            self.config = {
                "max_length": int(self.max_length_le.text()),
                "size": (int(self.size1_le.text()), int(self.size2_le.text())),
                "repeatframe": int(self.repeatframe_le.text()),
                "fps": float(self.fps_le.text()),
            }
        except ValueError:
            print("WARNING: invalid value in configurations")
        else:
            print("new cofig \n", self.config)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon('icons/favicon.svg'))
    mainWin = HelloWindow()
    mainWin.show()
    sys.exit(app.exec_())
