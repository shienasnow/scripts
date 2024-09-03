# Maya Asset Importer (ly, ani, lgt)
import sys
import os
import requests
import re
import subprocess
import platform
import json
from glob import glob
from configparser import ConfigParser
from pprint import pprint
from functools import partial
from shotgun_api3 import shotgun
import maya.cmds as cmds
try:
    from PySide6.QtWidgets import QApplication, QWidget, QGridLayout
    from PySide6.QtWidgets import QLabel, QCheckBox, QHBoxLayout
    from PySide6.QtWidgets import QMessageBox
    from PySide6.QtUiTools import QUiLoader
    from PySide6.QtGui import QPixmap, QIcon
    from PySide6.QtCore import QFile, QSize, Qt
    from PySide6.QtCore import Signal
except:
    from PySide2.QtWidgets import QApplication, QWidget, QGridLayout
    from PySide2.QtWidgets import QLabel, QCheckBox, QHBoxLayout
    from PySide2.QtWidgets import QMessageBox
    from PySide2.QtUiTools import QUiLoader
    from PySide2.QtGui import QPixmap, QIcon
    from PySide2.QtCore import QFile, QSize, Qt
    from PySide2.QtCore import Signal


class Import(QWidget):

    def __init__(self):
        super().__init__()

        self.connect_sg()
        self.get_user_id() # Loader를 통해서 마야를 실행했을 때 터미널에 남아 있는 user_id를 받아서 user_name을 찾는다
        self.make_ui()
        self.event_func() # 이벤트 함수 모음

        self.get_shot_info_from_current_directory() # 현재 작업 파일 경로에서 데이터 추출
        self.classify_task() # task 별로 다른 함수를 실행할 수 있도록 classyfy_task 함수에 task 전달

    def event_func(self):
        self.ui.tableWidget.itemSelectionChanged.connect(self.selected_asset_list) # 테이블 위젯 아이템 클릭할 때마다 썸네일 보이게
        self.label_img.doubleClicked.connect(self.open_thumbnail) # 썸네일 더블 클릭하면 이미지 오픈

        self.ui.pushButton_import.clicked.connect(self.import_assets) # Import 버튼 누르면 선택한 리스트의 에셋 Import
        self.ui.pushButton_import.clicked.connect(self.import_link_camera) # Import 버튼 누르면 rendercam이 Import

        self.ui.pushButton_refresh.clicked.connect(self.refresh_sg) # Refresh 버튼 누르면 샷그리드 연동 새로고침

    def connect_sg(self):
        URL = "https://4thacademy.shotgrid.autodesk.com"
        SCRIPT_NAME = "moomins_key"
        API_KEY = "gbug$apfmqxuorfqaoa3tbeQn"

        self.sg = shotgun.Shotgun(URL,
                                SCRIPT_NAME,
                                API_KEY)

    def get_user_id(self): # Loader를 통해 마야를 실행했을 때 user_id 받아오기
        try:
            self.user_id = os.environ["USER_ID"] # loader에서 publish, upload, import로 user_id 전달
        except:
            self.user_id = 121 # 임시

    def get_user_name(self): # user_id로 user_name 찾기
        user_info = self.sg.find_one("HumanUser", filters=[["id", "is", self.user_id]], fields=["name"])
        user_name = user_info["name"]
        return user_name

    def get_shot_info_from_current_directory(self): # project, seq_name, seq_num, task, version, shot_id 추출
        current_file_path = cmds.file(q=True, sn=True)
        print(f"현재 마야 파일 경로 : {current_file_path}")
        # /home/rapa/wip/Moomins/seq/AFT/AFT_0010/ly/wip/scene/v001/AFT_0010_v001_w001.mb

        project = current_file_path.split("/")[4] # Moomins
        seq_name = current_file_path.split("/")[6] # AFT
        self.seq_num = current_file_path.split("/")[7] # AFT_0010
        self.task = current_file_path.split("/")[8] # ly
        self.version = current_file_path.split("/")[11] # v001

        # seq num로 shot_id 찾기
        shot_filter = [["code", "is", self.seq_num]]
        shot_fields = ["id"]
        shot_entity = self.sg.find_one("Shot", filters=shot_filter, fields=shot_fields)
        self.shot_id = shot_entity['id']

        self.ui.label_project.setText(project)
        self.ui.label_sq.setText(seq_name)
        self.ui.label_sqnum.setText(self.seq_num)
        self.ui.label_task.setText(self.task)

        print(f"현재 작업 샷 넘버 : {self.seq_num} (id : {self.shot_id})")


# Task(ly, ani, lgt) 구분해서 다른 make ini 함수 실행
# Maya Shot 작업자가(ly, ani, lgt) 아닌 경우 아무것도 할 수 없도록
    def classify_task(self):
        print(f"현재 작업 Task : {self.task}")

        if self.task == "ly":
            print("레이아웃 작업을 시작합니다.\nlkd 또는 rig asset과 rendercam Import하세요.")
            self.get_ly_assigned_assets() # seq num에 부여된 asset들의 정보들을 찾아서 ini를 만든다.
            self.make_table_ui_for_ly() # ini 파일 받아서 ui에 넣기

        elif self.task == "ani":
            print("애니메이션 작업을 시작합니다.\nly과 rendercam Import하세요.")
            self.get_lgt_assgined_assets() # seq num가 같은 ly, ani, fx task의 정보들을 찾아서 ini를 만든다.
            self.make_table_ui_for_ani()

        elif self.task == "lgt":
            print("라이팅 작업을 시작합니다.\nly, ani, fx, rendercam Import하세요.")
            self.get_lgt_assgined_assets() # seq num가 같은 ly, ani, fx task의 정보들을 찾아서 ini를 만든다.
            self.make_table_ui_for_lgt()

        else:
            print("마야에서 에셋을 import할 수 있는 작업 상태가 아닙니다.")
            QMessageBox.about(self, "경고", "'Import Assets'는 maya를 사용하는 Shot 작업에서만 실행할 수 있습니다.\n현재 작업 중인 내용을 확인해주세요.")


# Layout : shot number에 태그된 asset들(mod.mb 또는 rig.mb)의 정보 찾기
    def get_ly_assigned_assets(self): # shot에 태그된 asset id들을 가져와서 list로 만들어서 다음 함수에 넘긴다
        filter = [["code", "is", self.seq_num]]
        field = ["assets"]
        assigned_assets = self.sg.find_one("Shot", filters=filter, fields=field)
        asset_list = assigned_assets["assets"]
        # print(asset_list)
        # [{'id': 1546, 'name': 'bat', 'type': 'Asset'},
        # {'id': 1479, 'name': 'car', 'type': 'Asset'},
        # {'id': 1547, 'name': 'joker', 'type': 'Asset'}]
        asset_id_list = []
        for asset in asset_list:
            asset_id = asset["id"] # 1546
            asset_id_list.append(asset_id)

        self.make_asset_ini_for_ly(asset_id_list) # shot에 부여된 asset id 리스트를 넘겨준다

    def make_asset_ini_for_ly(self, asset_id_list): # ★ asset id 기준으로 찾은 정보들을 self.asset.ini에 넣는다
        self.asset_ini_for_ly = ConfigParser()

        # SG Asset Entity에서 가져오는 것 : 각 Asset의 Name, Status, Task
        for asset_id in asset_id_list:
            filter = [["id", "is", asset_id]] # [1546, 1479, 1547]
            field = ["code", "sg_status_list", "tasks"]
            asset_info = self.sg.find("Asset", filters=filter, fields=field) # [{'type': 'Asset', 'id': 1546, 'code': 'bat', 'sg_status_list': 'wip', 'description': "str", 'image': 'https://sg-media-usor-01.~~'},  'tasks': [{'id': 6353, 'name': 'Cloth', 'type': 'Task'}, {'id': 6350, 'name': 'Concept', 'type': 'Task'}, {'id': 6352, 'name': 'Groom', 'type': 'Task'}, {'id': 6351, 'name': 'Lookdev', 'type': 'Task'}, {'id': 6348, 'name': 'Model', 'type': 'Task'}, {'id': 6349, 'name': 'Rig', 'type': 'Task'}]}]
            asset_info = asset_info[0]
            asset_name = asset_info["code"] # joker
            self.asset_ini_for_ly[asset_name] = {} # asset name을 section으로 사용

            # Asset에 연결된 모든 Task의 ID를 추출
            task_ids = [task['id'] for task in asset_info['tasks']] # [6353, 6350, 6352, 6351, 6348, 6349]

            # task ID로 작업자 정보, step 가져오기 (lkd, mod, rig 알파벳 순서)
            for task_id in task_ids:
                tasks_info = self.sg.find("Task", [["id", "is", task_id]], ["task_assignees", "step", "sg_status_list"])
                task_info = tasks_info[0]

                asset_artist = task_info["task_assignees"][0]["name"]
                asset_task = task_info["step"]["name"]
                asset_status = task_info["sg_status_list"]
                # print(f"{asset_name}, {asset_task} : {asset_status}")

                self.asset_ini_for_ly[asset_name]["asset artist"] = asset_artist
                self.asset_ini_for_ly[asset_name]["asset task"] = asset_task
                self.asset_ini_for_ly[asset_name]["asset status"] = asset_status

                # 경로를 task entity에서 sg_description으로 가져오기
                filter = [["id", "is", task_id]]
                field = ["sg_description"]
                path_info = self.sg.find_one("Task", filters=filter, fields=field)
                path_description = str(path_info["sg_description"]) # 펍된 파일 경로
                pub_file_name = os.path.basename(path_description) # BRK_0010_v001.mb
                self.asset_ini_for_ly[asset_name]["asset pub directory"] = path_description

                # task id로 updated at을 가져오기
                field2 = ["updated_at"]
                date_info = self.sg.find_one("Task", filters=filter, fields=field2)
                pub_dates = date_info["updated_at"]
                pub_date = str(pub_dates).split("+")[0]
                self.asset_ini_for_ly[asset_name]["asset pub date"] = pub_date

            file_exts = pub_file_name.split(".")[-1]
            file_ext = "." + file_exts
            version = pub_file_name.split(".")[0].split("_")[-1]
            self.asset_ini_for_ly[asset_name]["asset file ext"] = file_ext # .mb
            self.asset_ini_for_ly[asset_name]["asset version"] = version # v001


        # ini 파일 확인용 출력
        print("\n*&*&*&*&*&*&*&*&*&*&*&*&* ini 확인 *&*&*&*&*&*&*&*&*&*&*&*&")
        for section in self.asset_ini_for_ly.sections():
            for k, v in self.asset_ini_for_ly[section].items():
                print(f"{section}, {k}: {v}")
        #     # bat, asset status: wip
        #     # bat, asset pub directory: /home/rapa/pub/Moomins/asset/character/bat/rig/pub/scenes/v001/bat_v001.mb
        #     # bat, asset artist: 정현 염
        #     # bat, asset task: rig
        #     # bat, asset file ext: .mb
        #     # bat, asset version: v001
        #     # bat, asset pub date: 2024-08-23 17:21:08
        #     # joker, asset status: pub
        #     # joker, asset pub directory: /home/rapa/pub/Moomins/asset/character/joker/rig/pub/scenes/v001/joker_v001.mb
        #     # joker, asset artist: 정현 염
        #     # joker, asset task: rig
        #     # joker, asset file ext: .mb
        #     # joker, asset version: v001
        #     # joker, asset pub date: 2024-08-23 17:21:08


# Animation, Lighting : 같은 shot number에 해당되는 ly, ani, fx의 정보들 찾기
    def get_lgt_assgined_assets(self): # task id에 해당되는 ly, ani, fx의 abc 파일 경로를 찾습니다

        filter_ly = [["entity", "is", {"type" : "Shot", "id" : self.shot_id}], ["step", "is", {"type": "Step", "id": 277}]] # shot_id + ly의 step id
        filter_ani = [["entity", "is", {"type" : "Shot", "id" : self.shot_id}], ["step", "is", {"type": "Step", "id": 106}]] # shot_id + ani의 step id
        filter_fx = [["entity", "is", {"type" : "Shot", "id" : self.shot_id}], ["step", "is", {"type": "Step", "id": 276}]] # shot_id + fx의 step id
        field = ["id", "sg_description"] # pub abc 파일 경로, task id

        ly_asset_info = self.sg.find("Task", filters=filter_ly, fields=field)
        ani_asset_info = self.sg.find("Task", filters=filter_ani, fields=field)
        fx_asset_info = self.sg.find("Task", filters=filter_fx, fields=field)
        ly_asset_info = ly_asset_info[0]
        ani_asset_info = ani_asset_info[0]
        fx_asset_info = fx_asset_info[0]

        ly_asset_id = ly_asset_info["id"] # 6328
        ani_asset_id = ani_asset_info["id"] # 6326
        fx_asset_id = fx_asset_info["id"] # 6331
        ly_asset_directory = ly_asset_info["sg_description"] # /home/rapa/pub/Moomins/seq/AFT/AFT_0010/ly/pub/scenes/v001/AFT_0010_ly_v001.abc
        ani_asset_directory = ani_asset_info["sg_description"] # /home/rapa/pub/Moomins/seq/AFT/AFT_0010/ani/pub/scenes/v001/AFT_0010_ani_v001.abc
        fx_asset_directory = fx_asset_info["sg_description"] # /home/rapa/pub/Moomins/seq/AFT/AFT_0010/fx/pub/scenes/v001/AFT_0010_fx_v001.abc

        # shot_asset_id_list = [ly_asset_id, ani_asset_id, fx_asset_id]
        # shot_asset_list = [ly_asset_directory, ani_asset_directory, fx_asset_directory]
        shot_asset_dict = {}
        shot_asset_dict[ly_asset_id] = ly_asset_directory
        shot_asset_dict[ani_asset_id] = ani_asset_directory
        shot_asset_dict[fx_asset_id] = fx_asset_directory

        # self.get_ini_data_from_sg(shot_asset_id_list)
        self.make_asset_ini_for_lgt(shot_asset_dict)

    def make_asset_ini_for_lgt(self, shot_asset_dict): # ★ ly, ani, fx에서 pub한 파일의 정보가 담긴 ini 만들기
        self.asset_ini_for_lgt = ConfigParser()

        for asset_id, asset_directory in shot_asset_dict.items():

            filter = [["id", "is", asset_id]]
            asset_names = self.sg.find("Task", filters=filter, fields=["content", "step"])
            asset_names = asset_names[0] # {'type': 'Task', 'id': 6328, 'content': 'AFT_0010_ly', 'step': {'id': 277, 'name': 'ly', 'type': 'Step'}}
            asset_name = asset_names["content"] # AFT_0010_ly, AFT_0010_ani, AFT_0010_fx
            asset_task = asset_names["step"]["name"]


            file_name = os.path.basename(asset_directory) # AFT_0010_lgt_v001.abc
            file_ext = "." + file_name.split(".")[-1]

            # ani 경로에서 필요한 거 따기
            self.asset_ini_for_lgt[asset_name] = {}
            self.asset_ini_for_lgt[asset_name]["asset pub directory"] = asset_directory # 가져올 파일 경로
            self.asset_ini_for_lgt[asset_name]["asset task"] = asset_task # 해당 에셋의 task
            self.asset_ini_for_lgt[asset_name]["asset file ext"] = file_ext # .abc
            self.asset_ini_for_lgt[asset_name]["asset version"] = self.version # v001

            # sg에서 찾아서 가져오기 (asset artist, asset stuats, asset pub date)
            filter = [["id", "is", asset_id]]
            field = ["task_assignees", "sg_status_list", "updated_at"]
            sg_data = self.sg.find("Task", filters=filter, fields=field)
            sg_data = sg_data[0]
            asset_artist = sg_data["task_assignees"][0]["name"]
            asset_status = sg_data["sg_status_list"]
            asset_pub_date = sg_data["updated_at"]
            asset_pub_date = str(asset_pub_date).split("+")[0]

            self.asset_ini_for_lgt[asset_name]["asset artist"] = asset_artist # hyoeun seol
            self.asset_ini_for_lgt[asset_name]["asset status"] = asset_status # pub
            self.asset_ini_for_lgt[asset_name]["asset pub date"] = asset_pub_date # 2024-08-28 14:42:12

        # # self.asset_ini_for_lgt 출력 확인
        # for section in self.asset_ini_for_lgt.sections():
            for k, v in self.asset_ini_for_lgt[section].items():
                print(f"{section}, {k}: {v}")
            # AFT_0010_ly, asset pub directory: /home/rapa/pub/project/seq/AFT/AFT_0010/ly/pub/scenes/v001/AFT_0010_ly_v001.abc
            # AFT_0010_ly, asset task: ly
            # AFT_0010_ly, asset file ext: .abc
            # AFT_0010_ly, asset version: v001
            # AFT_0010_ly, asset artist: hyoeun seol
            # AFT_0010_ly, asset status: pub
            # AFT_0010_ly, asset pub date: 2024-08-28 15:26:44
            # AFT_0010_ani, asset pub directory: /home/rapa/pub/Moomins/seq/AFT/AFT_0010/ani/pub/scenes/v001/AFT_0010_ani_v001.abc
            # AFT_0010_ani, asset task: ly
            # AFT_0010_ani, asset file ext: .abc
            # AFT_0010_ani, asset version: v001
            # AFT_0010_ani, asset artist: 한별 박
            # AFT_0010_ani, asset status: wtg
            # AFT_0010_ani, asset pub date: 2024-08-28 14:42:06
            # AFT_0010_fx, asset pub directory: /home/rapa/pub/Moomins/seq/AFT/AFT_0010/fx/pub/scenes/v001/AFT_0010_fx_v001.abc
            # AFT_0010_fx, asset task: ly
            # AFT_0010_fx, asset file ext: .abc
            # AFT_0010_fx, asset version: v001
            # AFT_0010_fx, asset artist: seonil hong
            # AFT_0010_fx, asset status: wtg
            # AFT_0010_fx, asset pub date: 2024-08-28 14:42:12


# UI (현재 Task에 따라 필요한 ini 불러와서 UI에 넣기)
    def make_ui(self): # ui를 띄우고 하드 코딩 필요한 부분 추가 (아이콘, 썸네일)
        my_path = os.path.dirname(__file__)
        ui_file_path = my_path + "/asset_import.ui"

        ui_file = QFile(ui_file_path)
        ui_file.open(QFile.ReadOnly)
        loader = QUiLoader()
        self.ui = loader.load(ui_file, self)
        self.ui.show()
        ui_file.close()

        # Refresh 버튼 아이콘 png 넣기
        my_path = os.path.dirname(__file__) # 현재 파일 경로 (/home/rapa/env/maya/2023/scripts)
        img_path = my_path + "/sourceimages/refresh.png"
        icon = QIcon(img_path)
        icon_size = QSize(20, 20)
        self.ui.pushButton_refresh.setIcon(icon)
        self.ui.pushButton_refresh.setIconSize(icon_size)
        
        # 더블 클릭 할 수 있는 라벨 생성해서 vereticalLayout_2의 가장 상단에 넣기
        self.label_img = DoubleClickableLabel("THUMBNAIL")
        self.label_img.setFixedSize(364, 216) # 364 x 216 사이즈 고정
        self.label_img.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.ui.verticalLayout_2.insertWidget(0, self.label_img)

        user_name = self.get_user_name()        
        self.ui.label_artist.setText(user_name)

    def make_table_ui_for_ly(self): # asset 갯수만큼 컨테이너 생성하고 ini 정보를 컨테이너에 넣기

        # asset(lkd, rig) 갯수 만큼 컨테이너 한 칸씩 만들기
        row_count = len(self.asset_ini_for_ly.sections())
        self.ui.tableWidget.setRowCount(row_count)

        # self.asset_ini_for_ly에 모아놓은 에셋 정보들을 각 컨테이너에 넣기
        row_idx = 0
        for section in self.asset_ini_for_ly.sections():
            self.table_ui_contents(section, row_idx)
            row_idx += 1

        rendercam_path = self.get_link_camera_directory()
        self.ui.listWidget.insertItem(0, rendercam_path)

    def make_table_ui_for_ani(self): # lgt ini에서 ly만 추출해서 새로운 configParser 만들기
        self.asset_ini_for_ani = ConfigParser()
        for section in self.asset_ini_for_lgt.sections():
            # if self.asset_ini_for_lgt.has_option(section, "asset task") and self.asset_ini_for_lgt.get(section, "asset task" == "ly"):
            if self.asset_ini_for_lgt.get(section, "asset task") == "ly":
                self.asset_ini_for_ani.add_section(section)
                for k, v in self.asset_ini_for_lgt.items(section):
                    self.asset_ini_for_ani.set(section, k, v)

        # self.asset_ini_for_ani 출력 테스트
        # for section in self.asset_ini_for_ani.sections():
        #     for k, v in self.asset_ini_for_ani[section].items():
        #         print(f"{section}, {k}: {v}")
            # AFT_0010_ly, asset pub directory: /home/rapa/pub/Moomins/seq/AFT/AFT_0010/ly/pub/cache/v001/AFT_0010_ly_v001.abc
            # AFT_0010_ly, asset task: ly
            # AFT_0010_ly, asset file ext: .abc
            # AFT_0010_ly, asset version: v001
            # AFT_0010_ly, asset artist: hyoeun seol
            # AFT_0010_ly, asset status: pub
            # AFT_0010_ly, asset pub date: 2024-08-28 19:34:33

        # asset(ly) 갯수 만큼 컨테이너 한 칸씩 만들기
        row_count = len(self.asset_ini_for_ani.sections())
        self.ui.tableWidget.setRowCount(row_count)

        # self.asset_ini_for_ani에 모아놓은 에셋 정보들을 각 컨테이너에 넣기
        row_idx = 0
        for section in self.asset_ini_for_ani.sections():
            print ("section", section, row_idx)
            self.table_ui_contents(section, row_idx)
            row_idx += 1

        rendercam_path = self.get_link_camera_directory()
        self.ui.listWidget.insertItem(0, rendercam_path)

    def make_table_ui_for_lgt(self): # task asset(ly, ani, fx) 갯수만큼 컨테이너 생성하고 ini 정보를 컨테이너에 넣기

        # asset(ly, ani, fx) 갯수 만큼 컨테이너 한 칸씩 만들기
        row_count = len(self.asset_ini_for_lgt.sections())
        self.ui.tableWidget.setRowCount(row_count)
        
        # self.asset_ini_for_lgt에 모아놓은 에셋 정보들을 각 컨테이너에 넣기
        row_idx = 0
        for section in self.asset_ini_for_lgt.sections():
            print ("section", section, row_idx)
            self.table_ui_contents(section, row_idx)
            row_idx += 1

        rendercam_path = self.get_link_camera_directory()
        self.ui.listWidget.insertItem(0, rendercam_path)

    def table_ui_contents(self, section, row_idx): # UI 컨테이너에 넣을 내용 하드 코딩
        self.ui.tableWidget.setRowHeight(row_idx, 60)
        self.ui.tableWidget.setColumnCount(1)

        container_widget = QWidget()

        h_layout = QHBoxLayout()
        grid_layout = QGridLayout()

        # 체크박스 생성해서 h_ly에 넣기
        self.checkbox = QCheckBox()
        self.checkbox.setFixedWidth(20)
        h_layout.addWidget(self.checkbox) # 왼쪽에 체크박스 추가

        if self.task == "ly":
            ini = self.asset_ini_for_ly
        elif self.task == "ani":
            ini = self.asset_ini_for_ani
        elif self.task == "lgt":
            ini = self.asset_ini_for_lgt

        ### grid layout 생성해서 h_ly에 넣기
        # asset name
        label_asset_name = QLabel()
        label_asset_name.setObjectName("label_asset_name")
        label_asset_name.setText(section)
        label_asset_name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_asset_name.setStyleSheet("font-size: 14px;")
        label_asset_name.setFixedSize(100, 30)

        # asset status
        label_asset_status = QLabel()
        label_asset_status.setObjectName("label_asset_status")
        label_asset_status.setText(ini[section]["asset status"])
        label_asset_status.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_asset_status.setStyleSheet("font-size: 14px;")
        label_asset_status.setFixedSize(50, 30)
        # asset status에 따라서 아이콘으로 변경 필요 (status 종류 6개)
        # if self.asset_ini_for_ly[section]["asset status"] == "wtg":
            # label에 wtg Pixmap set하기
        # elif self.asset_ini_for_ly[section]["asset status"] == "wip":
            # label에 wip Pixmap set하기
        # elif self.asset_ini_for_ly[section]["asset status"] == "pub":
            # label에 pub Pixmap set하기
        # else: (fin)
            # label에 fin Pixmap set하기

        # asset artist
        label_asset_artist = QLabel()
        label_asset_artist.setObjectName("label_asset_artist")
        label_asset_artist.setText(ini[section]["asset artist"])
        label_asset_artist.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_asset_artist.setStyleSheet("font-size: 10px;")
        label_asset_artist.setFixedSize(100, 30)

        # asset task
        label_asset_task = QLabel()
        label_asset_task.setObjectName("label_asset_task")
        label_asset_task.setText(ini[section]["asset task"])
        label_asset_task.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_asset_task.setStyleSheet("font-size: 14px;")
        label_asset_task.setFixedSize(50, 30)

        # asset fileext
        label_asset_fileext = QLabel()
        label_asset_fileext.setObjectName("label_asset_fileext")
        label_asset_fileext.setText(ini[section]["asset file ext"])
        label_asset_fileext.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_asset_fileext.setStyleSheet("font-size: 14px;")
        label_asset_fileext.setFixedSize(50, 30)

        # asset version
        label_asset_version = QLabel()
        label_asset_version.setObjectName("label_asset_version")
        label_asset_version.setText(ini[section]["asset version"])
        label_asset_version.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_asset_version.setStyleSheet("font-size: 14px;")
        label_asset_version.setFixedSize(50, 30)

        # asset pub date
        label_asset_date = QLabel()
        label_asset_date.setObjectName("label_asset_date")
        label_asset_date.setText(ini[section]["asset pub date"])
        label_asset_date.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_asset_date.setStyleSheet("font-size: 10px;")
        # label_asset_date.setFixedSize(50, 30)

        # asset pub directory
        label_asset_pub_directory = QLabel()
        label_asset_pub_directory.setObjectName("label_asset_pub_directory")
        label_asset_pub_directory.setText(ini[section]["asset pub directory"])

        # 레이아웃에 라벨 삽입 (label, row, col)
        grid_layout.addWidget(label_asset_name, 0, 1, 2, 1)  # asset name
        grid_layout.addWidget(label_asset_version, 0, 3)     # asset version
        grid_layout.addWidget(label_asset_task, 0, 4)        # asset task
        grid_layout.addWidget(label_asset_fileext, 0, 5)     # asset fileext

        grid_layout.addWidget(label_asset_artist, 1, 1)      # asset artist
        grid_layout.addWidget(label_asset_date, 1, 2, 3, 1)  # asset pubdate
        grid_layout.addWidget(label_asset_status, 1, 5)      # asset status
        grid_layout.addWidget(label_asset_pub_directory, 1, 4) # asset pub directory
        label_asset_pub_directory.hide()

        h_layout.addLayout(grid_layout) # 오른쪽에 Grid layout 추가
        h_layout.setStretch(1, 1)

        # 컨테이너 위젯에 h_ly 설정
        container_widget.setLayout(h_layout)
        self.ui.tableWidget.setCellWidget(row_idx, 0, container_widget) # 테이블 위젯의 row_idx 행과 0열에 container_widget을 삽입

        # 체크 박스 상태 변경 시 listWidget에 들어가는 아이템 변경
        self.checkbox.toggled.connect(self.get_checked_row)
#################################################### status label 이미지로 변경 필요


# Thumbnail
    def selected_asset_list(self): # 테이블 위젯에서 선택한 에셋의 썸네일 경로를 추출해서 보여줌
        indexes = self.ui.tableWidget.selectedIndexes() # 다중 선택이 되기 때문에 Indexes

        for index in indexes:
            # asset이 pub된 경로를 찾아서 썸네일 이미지 경로로 바꾸기 위해서 폴더 경로 str replace!
            widget = self.ui.tableWidget.cellWidget(index.row(), 0)   # 테이블 위젯의 index.row()행과 0번째 열에 있는 셀의 위젯
            a = widget.findChild(QLabel, "label_asset_pub_directory") # 에셋 ini에서 label_asset_pub_directory인 QLabel
            original_path = a.text()                                  # 의 text를 찾는다

            # pub된 파일의 경로를 샷 업로더 캡처 경로와 같게 바꾸기 (여러 개일 수 있어서 가장 마지막 w버전 사용)
            if self.task == "ly":
                # 에셋 업로더의 캡처 경로 : /home/rapa/wip/Moomins/asset/character/jane/mod/wip/images/v002/jane_v002_w001.jpg
                folder_path = original_path.replace("scenes", "images").replace(".mb", ".jpg").replace("pub", "wip")
                directory_path = os.path.dirname(folder_path)
                image_path_list  = glob(os.path.join(directory_path, "*.jpg"))
                self.image_path = sorted(image_path_list)[-1]

            elif self.task in ["ani", "lgt"]:
                # 샷 업로더 캡처 경로  : /home/rapa/wip/Moomins/seq/AFT/AFT_0010/ly/wip/images/v001/AFT_0010_v001_w001.jpg #### 이렇게 바꾸기
                folder_path = original_path.replace("cache", "images").replace(".abc", ".jpg").replace("pub", "wip")
                directory_path = os.path.dirname(folder_path)
                image_path_list = glob(os.path.join(directory_path, "*.jpg"))
                self.image_path = sorted(image_path_list)[-1]

            pixmap = QPixmap(self.image_path)
            sclaed_pixmap = pixmap.scaled(364, 216)
            self.label_img.setPixmap(sclaed_pixmap)

    def open_thumbnail(self): # 더블 클릭시 썸네일 오픈
        print("더블 클릭")
        subprocess.Popen(['xdg-open', self.image_path])



# 체크 박스 토글 시 "테이블 위젯"의 체크 박스 기준으로 체크된 row의 정보들을 가져와서 listWidget에 넣는다.
    def get_checked_row(self): # 체크된 row들을 리스트로 가져옵니다
        checked_row_list = []
        row_count = self.ui.tableWidget.rowCount()

        for row in range(row_count):
            container = self.ui.tableWidget.cellWidget(row, 0)
            if container:
                h_layout = container.layout()
                checkbox = None
                for i in range(h_layout.count()):
                    widget = h_layout.itemAt(i).widget()
                    if isinstance(widget, QCheckBox):
                        checkbox = widget
                        break
                if checkbox and checkbox.isChecked():
                    checked_row_list.append(row)

        self.add_list_widget(checked_row_list)

    def add_list_widget(self, checked_row_list): # 체크된 row의 에셋 경로들 "리스트 위젯"에 넣기
        self.ui.listWidget.clear()
        rendercam_path = self.get_link_camera_directory()
        self.ui.listWidget.insertItem(0, rendercam_path) # rendercam 경로는 항상 맨 위에 들어가 있도록

        if self.task == "ly":
            ini = self.asset_ini_for_ly
        elif self.task == "ani":
            ini = self.asset_ini_for_ani
        elif self.task == "lgt":
            ini = self.asset_ini_for_lgt

        self.selected_list = []
        sections = ini.sections()
        for idx, section in enumerate(sections):
            if idx in checked_row_list: # 체크된 section만 가져오기
                selected_item = ini[section]["asset pub directory"]
                self.selected_list.append(selected_item)
        self.ui.listWidget.addItems(self.selected_list)



# Camera Import
    def get_link_camera_directory(self): # shot id 기준으로 카메라 경로 리턴
        filter = [["id", "is", self.shot_id]]
        field = ["description"]
        camera_info = self.sg.find_one("Shot", filters=filter, fields=field)
        shot_camera_directory = camera_info["description"]

        return shot_camera_directory

    def get_undistortion_size(self): # 매치무브 팀에서 샷그리드에 pub한 undistortion size를 받아옵니다
        # shot_id를 기준으로 undistortion size를 가져온다.
        filter = [["id", "is", self.shot_id]]
        field =["sg_undistortion_height", "sg_undistortion_width"]
        undistortion_info = self.sg.find_one("Shot", filters=filter, fields=field)
        undistortion_height = undistortion_info["sg_undistortion_height"] # 1220
        undistortion_width = undistortion_info["sg_undistortion_width"] # 2040

        return undistortion_height, undistortion_width

    def get_frame_range(self): # Frame Range는 (어디서 pub하지 않고) Plate에서부터 정해진 것
        # shot_id를 기준으로 frame range를 받아온다.
        filter = [["id", "is", self.shot_id]]
        field = ["sg_cut_in", "sg_cut_out"]
        frame_info = self.sg.find_one("Shot", filters=filter, fields=field)
        start_frame = frame_info["sg_cut_in"] # 1
        end_frame = frame_info["sg_cut_out"] # 25

        return start_frame, end_frame



# Asset Import (Import 버튼 누르면 선택된 list에 있는 아이템들 Import)
    def import_assets(self): # "리스트 위젯"에 있는 경로들을 현재 scene에 import
        print("선택한 asset들을 현재 scene으로 import하겠습니다")
        for path in self.selected_list:
            print(path)
            ext = os.path.basename(path).split(".")[-1]
            if ext == "mb":
                cmds.file(path, i=True, type="mayaBinary")
            elif ext == "abc":
                cmds.AbcImport(path, mode='import')
                
                
            # Import Shader
            self.import_shader()
            
            

    def import_link_camera(self): # Import 버튼 누르면 현재 seq number의 rendercam.abc를 현재 scene에 임포트합니다
        rendercam_path = self.get_link_camera_directory()
        print(f"{rendercam_path}\nRendercam Import!")
        cmds.AbcImport(rendercam_path, mode='import') #네임스페이스가 안붙음
        # cmds.file(camera_directory, reference=True, namespace=test_file) # reference import

    def refresh_sg(self): ###############################
        print("새로고침 실행. 샷그리드의 정보를 다시 읽어옵니다")
        #  비우고! 샷건데이터 불러오고! 넣어준다!



# Shader Import
################## 언제 실행해야 하지? shader import 버튼을 따로 만들까?
    def get_shader_path(self):
        print("가장 최근 shader.ma, shader.json이 link된 최종 shader 경로를 가져옵니다.")

        # /home/rapa/pub/Moomins/asset/prop/knife/lkd/pub/scenes/knife_lkd_shader_link.ma
        # /home/rapa/pub/Moomins/asset/prop/knife/lkd/pub/scenes/knife_lkd_json_link.json

        # /home/rapa/pub/{project}/{asset}/{asset_type}/{asset_name}/lkd/pub/scenes/{asset_name}_lkd_json_link.json
        return
    

    def import_shader(self):
        print("shader가 들어있는 shader.ma 파일과 shader assign 정보가 들어있는 shader.json을 불러와서 오브젝트에 붙이기")
        shader_ma_path, shader_json_path = self.get_shader_path()

        # maya name space 설정
        name_space = os.path.basename(shader_ma_path).split(".")[0]
        cmds.file(shader_ma_path, i=True, namespace=name_space)

        # json 파일 로드
        with open(shader_json_path, "r") as f:
            shader_dict = json.load(f)

        # shadere dictionary 정보대로 shader에 오브젝트 붙이기
        for shader, objects in shader_dict.items():
            name_space_shader = f"{name_space}:{shader}"
            cmds.select(clear=True)
            for oject in objects:
                cmds.select(object, add=True)
            cmds.hyperShade(assign=name_space_shader)


class DoubleClickableLabel(QLabel): # 더블 클릭 가능한 label 객체

    doubleClicked = Signal() # 더블클릭 시그널 정의

    def __init__(self, parent=None):
        super(DoubleClickableLabel, self).__init__(parent)

    def mouseDoubleClickEvent(self, event):
        # 더블클릭 이벤트가 발생했을 때 시그널을 방출합니다.
        super().mouseDoubleClickEvent(event)  # 기본 이벤트 처리
        self.doubleClicked.emit()  # 더블클릭 시그널 방출



if __name__ == "__main__":
    if not QApplication.instance():
        app = QApplication(sys.argv)
    win = Import()
    win.show()
    app.exec()