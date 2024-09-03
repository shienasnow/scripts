# Maya Asset Importer (ly, ani, lgt)
import sys
import os
import requests
import subprocess
import platform
from functools import partial
from shotgun_api3 import shotgun
from pprint import pprint
from configparser import ConfigParser
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
        self.make_ui()

        self.get_user_id() # Loader를 통해서 마야를 실행했을 때 터미널에 남아 있는 user_id를 가져온다
        self.current_shot_info() # ini 파일 생성 함수 모음 처음 실행
        self.make_table_ui() # ini 파일 받아서 ui에 넣기

        self.ui.tableWidget.itemSelectionChanged.connect(self.show_current_asset_info)

        self.ui.pushButton_import.clicked.connect(self.import_assets)
        self.label_img.doubleClicked.connect(self.open_thumbnail)

        self.ui.pushButton_reload.clicked.connect(self.reload_sg)

    def connect_sg(self):
        URL = "https://4thacademy.shotgrid.autodesk.com"
        SCRIPT_NAME = "moomins_key"
        API_KEY = "gbug$apfmqxuorfqaoa3tbeQn"

        self.sg = shotgun.Shotgun(URL,
                                SCRIPT_NAME,
                                API_KEY)

    def get_user_id(self):
        try:
            self.user_id = os.environ["USER_ID"]
            # Loader를 통해서 마야를 실행했을 때 터미널에 남아 있음
            # (loader에서 publish, upload, import로 user_id 전달)
            print(self.user_id)
        except:
            self.user_id = 121 # 임시



    def current_shot_info(self): # 현재 작업 경로
        current_file_path = cmds.file(q=True, sn=True)
        print(f"현재 마야 파일의 경로 : {current_file_path}")
        # /home/rapa/wip/Moomins/seq/AFT/AFT_0010/ly/wip/scene/v001/AFT_0010_v001_w001.mb

        project = current_file_path.split("/")[4] # Moomins
        seq_name = current_file_path.split("/")[6] # AFT
        seq_num = current_file_path.split("/")[7] # AFT_0010
        task = current_file_path.split("/")[8] # ly

        self.ui.label_project.setText(project)
        self.ui.label_sq.setText(seq_name)
        self.ui.label_sqnum.setText(seq_num)

        self.seq_num = seq_num
        self.get_assigned_assets() # seq num에 부여된 asset들을 찾는다
        self.classify_task(task) # task 별로 다른 함수를 실행할 수 있도록 classyfy_task 함수에 task 전달

    def classify_task(self, task): # ly, ani, lgt 구분
        print(f"현재 작업 경로에서 추출한 task 종류 : {task}")

        if task == "ly":
            print("레이아웃 작업입니다. asset을 불러와야 합니다.")

        elif task == "ani":
            print("애니메이션 작업입니다.")

        elif task == "lgt":
            print("라이팅 작업입니다")

        else:
            print("마야에서 에셋을 import할 수 있는 작업 상태가 아닙니다.")
            QMessageBox.about(self, "경고", "마야에서 에셋을 import할 수 있는 작업 상태가 아닙니다.")



### Layout Task의 경우
# shot에 태그된 asset 리스트를 가져와서 ui에 넣어준다
    def get_assigned_assets(self): # 1-1 shot에 태그된 asset id들을 가져온다
        print("시퀀스 넘버") # cup
        print(self.seq_num)
        filter = [["code", "is", self.seq_num]]
        field = ["assets"]
        assigned_assets = self.sg.find("Shot", filters=filter, fields=field)
        print(assigned_assets)
        # [{'type': 'Shot', 'id': 1353, 'assets': [
        # {'id': 1546, 'name': 'bat', 'type': 'Asset'},
        # {'id': 1479, 'name': 'car', 'type': 'Asset'},
        # {'id': 1547, 'name': 'joker', 'type': 'Asset'}]}]
        asset_list = assigned_assets[0]["assets"] # 리스트 풀기 위해서 [0] 필요
        # [{'id': 1546, 'name': 'bat', 'type': 'Asset'},
        # {'id': 1479, 'name': 'car', 'type': 'Asset'},
        # {'id': 1547, 'name': 'joker', 'type': 'Asset'}]

        asset_id_list = []
        for asset in asset_list:
            asset_id = asset["id"] # 1546
            asset_id_list.append(asset_id)

        self.get_ly_asset_info(asset_id_list) # shot에 부여된 asset id 리스트를 넘겨준다

    def get_ly_asset_info(self, asset_id_list): # ★★★ 1-2 assign된 asset id를 기준으로 asset에 대한 정보를 ini에 넣는다
        self.asset_ini = ConfigParser()

        # Shotgrid Asset 엔티티에서 가져오는 것
        for asset_id in asset_id_list:
            filter = [["id", "is", asset_id]] # [1546, 1479, 1547]
            field = ["code", "sg_status_list", "description", "image", "tasks"] # Asset Name, Asset Status, "description", "thumbnail", "tasks"
            asset_info = self.sg.find("Asset", filters=filter, fields=field) # [{'type': 'Asset', 'id': 1546, 'code': 'bat', 'sg_status_list': 'wip', 'description': "str", 'image': 'https://sg-media-usor-01.~~'},  'tasks': [{'id': 6353, 'name': 'Cloth', 'type': 'Task'}, {'id': 6350, 'name': 'Concept', 'type': 'Task'}, {'id': 6352, 'name': 'Groom', 'type': 'Task'}, {'id': 6351, 'name': 'Lookdev', 'type': 'Task'}, {'id': 6348, 'name': 'Model', 'type': 'Task'}, {'id': 6349, 'name': 'Rig', 'type': 'Task'}]}]
            asset_info = asset_info[0]

            asset_name = asset_info["code"] # joker
            asset_status = asset_info["sg_status_list"] # wip
            asset_description = asset_info["description"] # 펍된 파일 경로
            asset_thumbnail = asset_info["image"] # http...######################### 수정 필요

            self.asset_ini[asset_name] = {}
            self.asset_ini[asset_name]["asset status"] = asset_status
            # self.asset_ini[asset_name]["asset description"] = asset_description
            self.asset_ini[asset_name]["asset pub directory"] = asset_description
            # self.asset_ini[asset_name]["asset thumbnail"] = asset_thumbnail ########### 선생님이 알려주신 걸로 해결하기

            # Asset에 연결된 모든 Task의 ID를 추출
            task_ids = [task['id'] for task in asset_info['tasks']] # [6353, 6350, 6352, 6351, 6348, 6349]

            # task ID로 작업자 정보 가져오기
            for task_id in task_ids:
                tasks_info = self.sg.find("Task", [["id", "is", task_id]], ["task_assignees", "step"])
                task_info = tasks_info[0]
                asset_artist = task_info["task_assignees"][0]["name"] # 정현 염
                asset_task = task_info["step"]["name"]
                # print(asset_artist)
                # print(asset_task) # 마지막 스탭 구분하는 거 필요
                self.asset_ini[asset_name]["asset artist"] = asset_artist
                self.asset_ini[asset_name]["asset task"] = asset_task

            # Asset이 pub된 경로가 필요한 것
            # seq_num로 shot id를 찾는다
            shot_filter = [["code", "is", self.seq_num]]
            shot_fields = ["id"]
            shot_entity = self.sg.find_one("Shot", filters=shot_filter, fields=shot_fields)
            shot_id = shot_entity['id']
            self.shot_id = shot_id

            # task에서 그 shot id의 pub경로랑 업로드날짜를 찾는다.
            filter2 = [["step", "is", {'type': 'Step', 'id': 277}], ["entity", "is", {'type': 'Shot', 'id': shot_id}]]
            filter2 = [["entity", "is", {'type': 'Shot', 'id': shot_id}]]
            datas = self.sg.find('Task', filters=filter2, fields=["sg_description", "updated_at"])

            # pub_path = datas[0]["sg_description"]
            pub_path = asset_description
            # 어셋 /home/rapa/pub/Moomins/asset/character/bat/rig/pub/scenes/v001/bat_v001.mb
            # 샷 /home/rapa/pub/Marvelous/asset/prop/bat/rig/pub/scenes/v001/BRK_0010_v001.mb ??
            pub_file_name = os.path.basename(str(pub_path))

            file_ext = pub_file_name.split(".")[-1]
            file_ext = "." + file_ext
            version = pub_file_name.split(".")[0].split("_")[-1]
            pub_date = datas[0]["updated_at"]
            pub_date = str(pub_date).split("+")[0]

            self.asset_ini[asset_name]["asset file ext"] = file_ext # abc
            self.asset_ini[asset_name]["asset version"] = version # v001
            self.asset_ini[asset_name]["asset pub date"] = pub_date #shoggrid의 updated_at (Date Updated) 사용

        ### ini 파일 확인용 출력
        for section in self.asset_ini.sections():
            for k, v in self.asset_ini[section].items():
                print(f"{section}, {k}: {v}")
        # 이런 식으로 여러 asset 다 출력됨
            # bat, asset status: wip
            # bat, asset pub directory: /home/rapa/pub/Moomins/asset/character/bat/rig/pub/scenes/v001/bat_v001.mb
            # bat, asset artist: 정현 염
            # bat, asset task: rig
            # bat, asset file ext: .mb
            # bat, asset version: v001
            # bat, asset pub date: 2024-08-23 17:21:08
            # joker, asset status: pub
            # joker, asset pub directory: /home/rapa/pub/Moomins/asset/character/joker/rig/pub/scenes/v001/joker_v001.mb
            # joker, asset artist: 정현 염
            # joker, asset task: rig
            # joker, asset file ext: .mb
            # joker, asset version: v001
            # joker, asset pub date: 2024-08-23 17:21:08


    def make_ui(self): # 1-3 asset 정보를 ui에 배치해서 넣는다
        my_path = os.path.dirname(__file__)
        ui_file_path = my_path + "/asset_import.ui"

        ui_file = QFile(ui_file_path)
        ui_file.open(QFile.ReadOnly) # 이거 꼭 있어야 합니다
        loader = QUiLoader()
        self.ui = loader.load(ui_file, self)
        self.ui.show()
        # ui_file.close()

    def make_table_ui(self): # asset 갯수만큼 컨테이너 생상하고 각 asset 정보를 컨테이너에 넣기
        # Refresh 버튼 아이콘 png 추가

        my_path = os.path.dirname(__file__) # /home/rapa/env/maya/2023/scripts
        img_path = my_path + "/sourceimages/refresh.png"
        icon = QIcon(img_path)
        icon_size = QSize(20, 20)
        self.ui.pushButton_reload.setIcon(icon)
        self.ui.pushButton_reload.setIconSize(icon_size)
        
        # 더블 클릭 할 수 있는 라벨 생성해서 vereticalLayout_2의 가장 상단에 넣기
        self.label_img = DoubleClickableLabel("THUMBNAIL")
        self.label_img.setFixedSize(364, 216) # 314 x 216 사이즈 고정
        self.ui.verticalLayout_2.insertWidget(0, self.label_img)

        # 에셋 갯수만큼 컨테이너 한 칸씩 만들기
        row_count = len(self.asset_ini.sections())
        self.ui.tableWidget.setRowCount(row_count)

        # asset_ini에 모아놓은 에셋 정보들을 각 컨테이너에 넣습니다
        row_idx = 0
        for section in self.asset_ini.sections():
            self.table_ui_contents(section, row_idx)
            row_idx += 1

    def table_ui_contents(self, section, row_idx): # UI 하드 코딩
        self.ui.tableWidget.setRowHeight(row_idx, 60)
        self.ui.tableWidget.setColumnCount(1)

        container_widget = QWidget()

        h_layout = QHBoxLayout()
        grid_layout = QGridLayout()

    # 체크박스 생성해서 h_ly에 넣기
        self.checkbox = QCheckBox()
        self.checkbox.setFixedWidth(20)
        h_layout.addWidget(self.checkbox) # 왼쪽에 체크박스 추가
        self.checkbox.toggled.connect(self.get_checked_row) # 체크박스 상태 변경 시 함수 호출

    # grid layout 생성해서 h_ly에 넣기
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
        label_asset_status.setText(self.asset_ini[section]["asset status"])
        label_asset_status.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_asset_status.setStyleSheet("font-size: 14px;")
        label_asset_status.setFixedSize(50, 30)
        # asset status에 따라서 아이콘으로 변경 필요
        # if self.asset_ini[section]["asset status"] == "wtg":
        # elif self.asset_ini[section]["asset status"] == "wip":
        # elif self.asset_ini[section]["asset status"] == "pub":
        # else: (fin)

        # asset artist
        label_asset_artist = QLabel()
        label_asset_artist.setObjectName("label_asset_artist")
        label_asset_artist.setText(self.asset_ini[section]["asset artist"])
        label_asset_artist.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_asset_artist.setStyleSheet("font-size: 14px;")
        label_asset_artist.setFixedSize(100, 30)

        # asset task
        label_asset_task = QLabel()
        label_asset_task.setObjectName("label_asset_task")
        label_asset_task.setText(self.asset_ini[section]["asset task"])
        label_asset_task.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_asset_task.setStyleSheet("font-size: 14px;")
        label_asset_task.setFixedSize(50, 30)

        # asset fileext
        label_asset_fileext = QLabel()
        label_asset_fileext.setObjectName("label_asset_fileext")
        label_asset_fileext.setText(self.asset_ini[section]["asset file ext"])
        label_asset_fileext.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_asset_fileext.setStyleSheet("font-size: 14px;")
        label_asset_fileext.setFixedSize(50, 30)

        # asset version
        label_asset_version = QLabel()
        label_asset_version.setObjectName("label_asset_version")
        label_asset_version.setText(self.asset_ini[section]["asset version"])
        label_asset_version.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_asset_version.setStyleSheet("font-size: 14px;")
        label_asset_version.setFixedSize(50, 30)

        # asset pub date
        label_asset_date = QLabel()
        label_asset_date.setObjectName("label_asset_date")
        label_asset_date.setText(self.asset_ini[section]["asset pub date"])
        label_asset_date.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_asset_date.setStyleSheet("font-size: 10px;")
        # label_asset_date.setFixedSize(50, 30)

        # asset pub directory
        label_asset_pub_directory = QLabel()
        label_asset_pub_directory.setObjectName("label_asset_pub_directory")
        label_asset_pub_directory.setText(self.asset_ini[section]["asset pub directory"])

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


    def show_current_asset_info(self): # 선택한 에셋 pub directory로 썸네일 경로 추출해서 보여줌
        indexes = self.ui.tableWidget.selectedIndexes() # 다중 선택도 된다!

        for index in indexes:
            widget = self.ui.tableWidget.cellWidget(index.row(), 0)
            a = widget.findChild(QLabel, "label_asset_pub_directory")

            original_path = a.text() # /home/rapa/pub/Moomins/asset/character/joker/rig/pub/scenes/v001/joker_v001.mb
            self.image_path = original_path.replace("scenes", "images").replace(".mb", ".jpg")
            print(self.image_path)
            pixmap = QPixmap(self.image_path)
            sclaed_pixmap = pixmap.scaled(364, 216)
            self.label_img.setPixmap(sclaed_pixmap)

    def open_thumbnail(self): # 더블 클릭시 썸네일 오픈
        print("더블 클릭")
        subprocess.Popen(['xdg-open', self.image_path])


### Animation Task의 경우
# shot entity에서 "ly pub directory.abc" (sg_description)
# Link Camera Directory (func return 값)
    def get_ani_asset_info(self):
        print("Animation 작업에 필요한 데이터들을 정리합니다.")


### Lighting Task의 경우
# shot entity에서 ly pub directory.abc (sg_description)
# shot entity에서 ani pub directory.abc (sg_description)
# shot entity에서 fx pub directory.abc (sg_description)
# Link Camera Directory (func return 값)
    def get_lgt_asset_info(self):
        print("Lighting 작업에 필요한 데이터들을 정리합니다.")




    def get_link_camera_directory(self): # shot id 기준으로 카메라 경로 리턴
        print("최종 카메라 경로를 가져옵니다.")
        filter = [["id", "is", self.shot_id]]
        field = ["description"]
        camera_info = self.sg.find_one("Shot", filters=filter, fields=field)
        shot_camera_directory = camera_info["description"]

        return shot_camera_directory

    def import_link_camera(self):
        print("Import 버튼 누르면 최종 카메라.abc를 현재 씬에 임포트합니다.")






# 체크박스에 변경 사항이 생길 때마다 "테이블 위젯"의 체크 박스를 기준으로 체크된 row의 정보들을 가져옵니다.
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
        self.selected_list = []
        self.selected_list.append("카메라 pub 경로") # 카메라 에셋은 자동으로 "리스트 위젯"에 넣어진다. (주석 코드로 보충)

        sections = self.asset_ini.sections()
        for idx, section in enumerate(sections):
            # print(idx, section)
            # 0 bat
            # 1 joker
            if idx in checked_row_list: # 체크된 section만 가져오기
                selected_item = self.asset_ini[section]["asset pub directory"]
                self.selected_list.append(selected_item)
        self.ui.listWidget.addItems(self.selected_list)



# 버튼을 누르면
    def import_assets(self): # "리스트 위젯"에 있는 경로의 파일들을 현재 scene에 import
        print("선택한 asset들을 현재 scene으로 import하겠습니다")
        for path in self.selected_list:
            print(path)
            ext = os.path.basename(path).split(".")[-1]
            if ext == "mb":
                cmds.file(path, i=True, type="mayaBinary")
            elif ext == "abc":
                cmds.AbcImport(path, mode='import')

    def reload_sg(self): ############################################## 제대로 되는지 확인 필요
        print("새로고침 실행. 샷그리드의 정보를 다시 읽어옵니다")
        self.get_assigned_assets()
        self.make_ui()
        self.make_table_ui()















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