# Asset Publish
import os
import sys
import re
import subprocess
import maya.cmds as cmds
import maya.mel as mel
from maya  import OpenMayaUI as omui
from shiboken2 import wrapInstance
from shotgun_api3 import shotgun

try:
    from PySide6.QtWidgets import QApplication, QLabel, QTextEdit
    from PySide6.QtWidgets import QWidget, QPushButton, QMessageBox
    from PySide6.QtGui import *
    from PySide6.QtUiTools import QUiLoader
    from PySide6.QtCore import QFile
except:
    from PySide2.QtWidgets import QApplication, QLabel, QTextEdit
    from PySide2.QtWidgets import QWidget, QPushButton, QMessageBox
    from PySide2.QtUiTools import QUiLoader
    from PySide2.QtCore import QFile, Qt

class ShotPublish(QWidget):
    def __init__(self):
        super().__init__()

        self.make_ui()

    def make_ui(self):
        my_path = os.path.dirname(__file__)
        ui_file_path = my_path +"/shot_publish.ui"

        ui_file = QFile(ui_file_path)
        ui_file.open(QFile.ReadOnly) # 이거 꼭 있어야 합니다
        loader = QUiLoader()
        self.ui = loader.load(ui_file, self)
        ui_file.close()


if __name__ == "__main__":
    if not QApplication.instance():
        app = QApplication(sys.argv)
    win = ShotPublish()
    win.show()
    app.exec()