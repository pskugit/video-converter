import sys
import cv2
import time
import tqdm
import os
import numpy as np
import imageio
from os import listdir
from os.path import isfile, join
from pathlib import Path


from PyQt5.QtWidgets import QMainWindow, QLabel,QGridLayout, QWidget, QPushButton, QFileDialog, QApplication, QProgressBar
from PyQt5.QtCore import QSize, Qt, QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5 import QtGui, QtCore, uic
import traceback,sys

sys.path.insert(0, 'D:\\pj-val-ml')
print(sys.path)
from pjval_ml.utils.mpc2_5.crbc2ispluv import CrbcToIspLuv, ispLuvToSRgb


if QtCore.QT_VERSION>=0x50501:
	def excepthook(type_,value,traceback_):
		traceback.print_exception(type_,value,traceback_)
		QtCore.qFatal('')
sys.excepthook=excepthook

class Worker(QObject):
    def __init__(self, filenames, config):
        super(Worker, self).__init__()
#        self.call_f1.connect(self.f1)
#        self.call_f2.connect(self.f2)

        self.filenames = filenames
        self.config = config

    progress = pyqtSignal(float)
    call_video = pyqtSignal()
    call_images = pyqtSignal()
    finished = pyqtSignal()

    @pyqtSlot()
    def run(self, some_string_arg):
        self.function(*self.args, **self.kwargs)

    @pyqtSlot()
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
                print("while ret")
                filename = str(i).rjust(width,"0")+'.png'
                for _ in range(skipframes+1):
                    ret, frame = cap.read()
                print(ret)
                if ret:
                    cv2.imwrite(dir+"\\"+filename, frame)
                    print("saves", dir+"\\"+filename)
                    self.progress.emit(100 * ((i*(skipframes+1)) / length))
                    i += 1
            self.finished.emit()
        finally:
            cap.release()

    @pyqtSlot()
    def video(self):
        #### PARAMETERS
        container = ".mp4"
        codec = "HEVC"
        if self.config["max_length"] > 0:
            max_length = min(self.config["max_length"], len(self.filenames))
        else:
            max_length = len(self.filenames)
        size = self.config["size"]  # bluefox: (2464, 2056) 0,8344.....   0,5625
        repeatframe = self.config["repeatframe"]
        fps = self.config["fps"]
        is_ccda4 = self.config["is_ccda4"]

        self.filenames = self.filenames[:max_length]
        name = "video_" + time.strftime("%y_%m_%d_%H-%M-%S", time.localtime()) + container
        output_path = "videos/" + name
        output = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*codec), fps, size)
        length = len(self.filenames)
        for idx, file in tqdm.tqdm(enumerate(self.filenames)):
            if is_ccda4:
                frame = imageio.imread(file)
                ispL, ispUv = CrbcToIspLuv(frame)()
                frame = ispLuvToSRgb(ispL, ispUv)
                frame = (frame * 255).astype(np.uint8)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
            # frame = cv2.resize(frame, None, fx=0.5, fy=0.5)
            # frame = cv2.resize(frame, size, interpolation=cv2.INTER_LINEAR)
                frame = cv2.imread(file)
                (oldw, oldh, depth) = frame.shape
                woffset = (oldw - size[0]) // 2
                hoffset = (oldh - size[1]) // 2
                frame = frame[hoffset:hoffset + size[1], woffset:woffset + size[0]]

            for i in range(repeatframe):
                # cv2.imshow('Image', frame)
                # k = cv2.waitKey(0)
                # if k == 27:
                #     cv2.destroyAllWindows()
                output.write(frame)
            self.progress.emit(100 * ((idx + 1) / length))
        output.release()
        print("Saved Video in", output_path)
        print("Number of frames:", len(self.filenames) * repeatframe)
        self.finished.emit()

class HelloWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setMinimumSize(QSize(440, 180))
        uic.loadUi("mv3_gui.ui",self)
        self.setWindowTitle("Videomaker")

        self.mv_button.setEnabled(False)
        self.config = {
            "max_length": 60,
            "size": (1280, 720),  # bluefox: (2464, 2056) 0,8344.....   0,5625
            "repeatframe": 1,
            "fps": 15,
            "is_ccda4": False,
        }
        self.mode = "f2v"
        self.progress.setValue(0)
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
        self.ccda4_checkbox.clicked.connect(self.update_config)
        self.mode_slider.valueChanged.connect(self.change_mode)

    @pyqtSlot(float)
    def on_progress(self, value):
        self.progress.setValue(value)

    @pyqtSlot()
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
        dlg = QFileDialog()
        if self.mode == "f2v":
            folder = dlg.getExistingDirectory(self, 'Select video folder', os.getcwd())
            self.data_label.setText(folder)
            try:
                print("Loading data...")
                files = listdir(folder)
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
        self.my_thread = QThread()
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

    @pyqtSlot(int)
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

    def update_config(self):
        try:
            self.config = {
                "max_length": int(self.max_length_le.text()),
                "size": (int(self.size1_le.text()), int(self.size2_le.text())),  # bluefox: (2464, 2056) 0,8344.....   0,5625
                "repeatframe": int(self.repeatframe_le.text()),
                "fps": float(self.fps_le.text()),
                "is_ccda4": self.ccda4_checkbox.isChecked(),
            }
        except ValueError:
            print("WARNING: invalid value in configurations")
        else:
            print("new cofig \n", self.config)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon('icons/favicon.svg'))
    mainWin = HelloWindow()
    mainWin.show()
    sys.exit(app.exec_())
