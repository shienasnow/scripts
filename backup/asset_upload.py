from maya import OpenMayaUI as omui
import maya.cmds as cmds
import sys
import os
import re
import subprocess
import datetime
try:
    from PySide6.QtWidgets import QWidget,QApplication,QLabel
    from PySide6.QtWidgets import QGridLayout,QTableWidget,QMessageBox
    from PySide6.QtWidgets import QApplication
    from PySide6.QtUiTools import QUiLoader
    from PySide6.QtCore import QFile,Qt,QTimer
    from PySide6.QtGui import QPixmap
    from shiboken6 import wrapInstance
except:
    from PySide2.QtWidgets import QWidget,QApplication,QLabel
    from PySide2.QtWidgets import QGridLayout,QTableWidget,QMessageBox
    from PySide2.QtWidgets import QApplication
    from PySide2.QtUiTools import QUiLoader
    from PySide2.QtCore import QFile,Qt,QTimer
    from PySide2.QtGui import QPixmap
    from shiboken2 import wrapInstance
from pprint import pprint
from capture import capturecode

class AssetUpload(QWidget):

    def __init__(self,parent=None):
        super(AssetUpload, self).__init__(parent)
        self.camera_transform = None
        self.make_ui()
        self.set_input_path()
        self.set_text_label()
        self.event_func()
        
    def set_input_path(self):
        """
        id를 받아 artist의 이름을 찾아 slate에 넣어주어야 한다.
        """
        ex_path = "/home/rapa/wip/Marvelous/asset/Character/dami/modeling/wip/scenes/v001/dami_v001_w001.mb"
        artist_name = "damiKim"
        split_path = ex_path.split("/")
        project = split_path[4]
        asset_type = split_path[6]
        asset_name = split_path[7]
        task = split_path[8]
        open_file_name = os.path.basename(ex_path)               # dami_v001_w001.mb
        open_file_path = os.path.dirname(ex_path)                # /home/rapa/wip/Marvelous/asset/Character/dami/modeling/wip/scenes/v001
        render_file_path = f"/home/rapa/wip/{project}/asset/{asset_type}/{asset_name}/{task}/wip/images"
        only_file_name,_=  os.path.splitext(open_file_name) # dami_v001_w001, .mb
        version = only_file_name.split("_")[1]    # v001
        self.file_data_list = [project,asset_type,asset_name,task,version,artist_name]
        #['Marvelous', 'Character', 'dami', 'modeling', 'v001', '다미김']
        self.render_data_list = [render_file_path,only_file_name]
        #['/home/rapa/wip/Marvelous/asset/Character/dami/modeling/wip/images', 'dami_v001_w001']
        
        
    def make_ui(self):
        my_path = os.path.dirname(__file__)
        ui_file_path = my_path + "/asset_upload.ui"

        ui_file = QFile(ui_file_path)
        loader = QUiLoader()
        self.ui = loader.load(ui_file, self)
        ui_file.close()
        self.table = self.ui.findChild(QTableWidget, "tableWidget")     # table위젯을 찾아서 table 로정의해준다.
        layout = QGridLayout(self)
        layout.addWidget(self.ui)
        self.setLayout(layout)
        self.setMinimumSize(640, 500)

    def set_text_label(self):
        project,asset_type,asset_name,task,version,artist_name = self.file_data_list
        render_file_path,only_file_name = self.render_data_list
        pattern = re.compile(f"asset/([^/]+?)/{asset_name}")    # asset/과 /asset_name의 사이에있는 filetype을 가져온다. => 스플릿하기 너무 귀찮았음
        match = pattern.search(render_file_path)
        if not match:
            return
        asset_type = match.group(1)
        
        # Moomin_path = "/home/rapa/test_image/Moomin.jpg"
        # pixmap = QPixmap(Moomin_path)
        # scaled_pixmap = pixmap.scaled(80, 80)
        # self.ui.label_Moomin.setPixmap(scaled_pixmap) # 소스 이미지 폴더 공유 후에 다시 하던지 할게요 - 효은
        self.ui.label_asset_name.setText(asset_name)
        self.ui.label_asset_type.setText(asset_type)
        self.ui.label_version.setText(version)
        self.ui.label_ext.setText("mb")

    def event_func(self):
        self.ui.pushButton_set.clicked.connect(self.push_set_turn_table_button)
        self.ui.pushButton_render.clicked.connect(self.push_render_turn_table_button)
        self.ui.pushButton_capture.clicked.connect(self.push_capture_image_button)
        self.table.cellDoubleClicked.connect(self.double_click_table_widget)

    def push_set_turn_table_button(self):   # 카메라가 생성되고 오브젝트 그룹이 잡히면서 키만 들어가야한다.
        selected_objects = cmds.ls(selection=True)                                                                  # 선택한 오브젝트가 없으면 돌아가라.
        if not selected_objects:
            self.msg_box("NoneSelectObject")
            return
        cmds.playbackOptions(min=1, max=100)                                                                            # 1프레임부터 200프레임까지 설정
        camera_transform,camera_shape = cmds.camera(name="turntable_camera#")                                           # camera 생성
        cmds.setAttr(f"{camera_shape}.orthographic", 0)                                                                 # 카메라 시점 perspective로 변경
        camera_position = (10, 10, 15)
        cmds.xform(camera_transform, ws=True, translation=camera_position)
        turntable_camera_grp = cmds.group(empty = True, name = "turntable_camera_grp")                                  # camera group화
        cmds.parent(camera_transform,turntable_camera_grp)                                                              # 부모자식 만들기
        cmds.xform(turntable_camera_grp, ws=True, translation=(0, 0, 0))                                                # 카메라 월드축 0,0,0으로 만들기
        
        cmds.lookThru(camera_transform)
        
        
        cmds.setAttr(f"{camera_transform}.rotateX", -30)                                                                # 내가 직접 해보고 그나마 잘보이는수치
        cmds.setAttr(f"{camera_transform}.rotateY", 35)
    
        cmds.setKeyframe(turntable_camera_grp,attribute="rotateY",time=1,value=0)                                       # 1프레임 rotateY key == 0 
        cmds.setKeyframe(turntable_camera_grp,attribute="rotateY",time=100,value=360)                                   # 100프레임 rotateY key == 100
        cmds.keyTangent(turntable_camera_grp,attribute="rotateY",inTangentType="linear",outTangentType="linear")        # 애니메이션 linear
        self.camera_transform = camera_transform

    def push_render_turn_table_button(self):

        render_icon_path = "/home/rapa/test_image/movicon.jpg"
        
        render_file_path,only_file_name =  self.render_data_list
        #['/home/rapa/wip/Marvelous/asset/Character/dami/modeling/wip/images', 'dami_v001_w001']
        start_frame = 1
        end_frame = 100  
        image_file_path = f"{render_file_path}/{only_file_name}"
        # /home/rapa/wip/Marvelous/asset/Character/dami/modeling/wip/images/dami_v001_w001
        file_format = "jpg" 
        
        if not self.camera_transform:
            return
        
        model_panel = cmds.getPanel(withFocus=True)                                 # 자신이 보고있는 뷰포트 패널을 가져온다
        if not model_panel or cmds.getPanel(typeOf=model_panel) != 'modelPanel':    # modelPanel인지 확인 >> 잘모르겠음
            return
        cmds.modelPanel(model_panel, edit=True, camera=self.camera_transform)
        
        cmds.playblast(
        startTime=start_frame,              # 시작프레임
        endTime=end_frame,                  # 끝프레임
        format="image",                     # 포맷을 image로 설정
        filename=image_file_path,           # 이미지 이름이 포함된 총 파일 경로.
        widthHeight=(1920, 1080),           # 이미지 해상도 설정.        # 동영상이 왜 깨지는지 모르겠음
        sequenceTime=False,
        clearCache=True,
        viewer=False,                       # 플레이블라스트 후 바로 재생하지 않음
        showOrnaments=False,                # UI 요소 숨김
        fp=4,                               # 프레임 패딩 ex) _0001
        percent=100,                        # 해상도 백분율
        compression=file_format,            # 코덱 설정
        quality=100,                        # 품질 설정
        )
        self.add_row_to_table("Rendering",render_icon_path)
        self.msg_box("ImageRenderComplete")
        # dami_v001_w001.0001.jpg
        self.make_mov_use_ffmpeg()

    def make_mov_use_ffmpeg(self):
        render_file_path,only_file_name = self.render_data_list
        input_file = os.listdir(render_file_path)[0]         # dami_v001_w001.0001.jpg
        replace_file = input_file.replace("0001","%04d")     # dami_v001_w001.%04d.jpg
        command_file = f"{render_file_path}/{replace_file}"
        
        project,asset_type,asset_name,task,version,artist_name = self.file_data_list
        resolution = "scale=1920:1080"
        font_path = "/home/rapa/문서/font/CourierPrime-Regular.ttf"
        padding = "drawbox=x=0:y=0:w=iw:h=ih*0.07:color=black:t=fill,drawbox=x=0:y=ih*0.93:w=iw:h=ih*0.07:color=black:t=fill"
        gamma = "-gamma 2.2"
        framerate = "-framerate 24"
        codec = "-c:v prores_ks"
        date = datetime.datetime.now().strftime("%Y-%m-%d") # 렌더링하는 날짜.

        left_top_text = f"drawtext=fontfile={font_path}:text={asset_name}:x=10:y=10:fontsize=50:fontcolor=white@0.7"
        mid_top_text = f"drawtext=fontfile={font_path}:text={project}:x=(1920-text_w)/2:y=10:fontsize=50:fontcolor=white@0.7"
        right_top_text = f"drawtext=fontfile={font_path}:text={date}:x=(1920-text_w)-10:y=10:fontsize=50:fontcolor=white@0.7"
        left_bot_text = f"drawtext=fontfile={font_path}:text={task}:x=10:y=(1080-text_h)-10:fontsize=50:fontcolor=white@0.7"
        mid_bot_text = f"drawtext=fontfile={font_path}:text={only_file_name}:x=(1920-text_w)/2:y=(1080-text_h)-10:fontsize=50:fontcolor=white@0.7"
        right_bot_text = f"drawtext=fontfile={font_path}:text={artist_name}:x=(1920-text_w)-10:y=(1080-text_h)-10:fontsize=50:fontcolor=white@0.7"

        command_list = [
            "ffmpeg",
            gamma,
            framerate,
            f"-i {command_file}",
            f"-vf '{padding},{resolution},{left_top_text},{mid_top_text},{right_top_text},{left_bot_text},{mid_bot_text},{right_bot_text}'",
            codec,
            f"{self.full_path}",
            "-y"
        ]

        # 리스트를 공백으로 구분하여 결합
        command = " ".join(command_list)
                
        process = subprocess.Popen(command, 
                               stdout=subprocess.PIPE,   # python 코드를 읽을수 있게 하는 코드
                               stderr=subprocess.STDOUT, # 오류메세지 표준출력s
                               universal_newlines=True,  # 줄바꿈 자동
                               shell=True
                               )


        for line in process.stdout:     # 디버깅 코드
            print(line, end='')
        for i in range(1,101):
            file_index = "%04d" % i
            remove_file = command_file.replace("%04d",file_index)
            os.remove(remove_file)

        process.wait()

# @Slot
    def call_back_capture(self,value):
        if value == True:
            self.timer = QTimer()
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(lambda: self.add_row_to_table("Capture", self.capture_path))
            self.timer.start(1000)
            print("complete")

    def push_capture_image_button(self):

        render_file_path,only_file_name = self.render_data_list
        capture_name = only_file_name + ".captureimage.jpg"
        self.capture_path = f"{render_file_path}/{capture_name}"
        
        
        self.capture = capturecode.Capture(self.capture_path)   
        self.capture.SIGNAL_JS.connect(self.call_back_capture)  
        self.capture.show()

    def msg_box(self,message_type): # 알림 메세지 띄우는 함수..
    
        if message_type == "NoneSelectObject":
            QMessageBox.critical(self, "Error", "None Selected objectgroup", QMessageBox.Yes)
        if message_type == "ImageRenderComplete":
            QMessageBox.information(self, "Complete", "Image Render Complete", QMessageBox.Ok)
        if message_type == "NoneFile":
            QMessageBox.critical(self, "Error", "파일이 없습니다.", QMessageBox.Yes)

    def double_click_table_widget(self):
        select_index = self.table.currentRow()
        if select_index == 0:
            try:
                subprocess.run(["vlc", self.full_path])
            except FileNotFoundError:
                self.msg_box("NoneFile")
        else:
            try:
                subprocess.Popen(['xdg-open', self.capture_path])
            except FileNotFoundError:
                self.msg_box("NoneFile")

    def add_row_to_table(self,type,icon_path):
        
        # self.add_row_to_table(0, "Rendering")

        
        render_file_path,only_file_name = self.render_data_list
        __,___,asset_name,task,version,artist_name = self.file_data_list
        self.full_path = f"{render_file_path}/{only_file_name}.mov"
        
        if type == "Rendering":
            path = self.full_path
            row_idx = 0
            ext = "mov"
        else:
            path = icon_path
            row_idx = 1
            ext = "jpg"
        thumbnail_image_path = icon_path
        row_count = self.table.rowCount()
        if row_idx >= row_count:
            self.table.setRowCount(row_idx + 1)
            
            
        self.make_table_hard_coding(row_idx, thumbnail_image_path, task, asset_name, version, ext, path)

    def make_table_hard_coding(self,row_idx, thumbnail_image_path, task, asset_name, version, ext, path): # 하드코딩한 함수...
        """
        하드 코딩으로 ui 만들기...!
        """
        
        self.table.setRowCount(2) 
        self.table.setColumnCount(1)
        self.table.setColumnWidth(0, 570)
        for i in range(2):
            self.table.setRowHeight(i, 90)
        
        
        
        label_icon_image = QLabel() 
        pixmap = QPixmap(thumbnail_image_path)
        scaled_pixmap = pixmap.scaled(80, 80)
        label_icon_image.setAlignment(Qt.AlignLeft)
        label_icon_image.setPixmap(scaled_pixmap)
        label_icon_image.setFixedSize(80,80)
        
        


        label_task = QLabel()
        label_task.setText(task)
        label_task.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label_task.setObjectName("task")
        label_task.setStyleSheet("font-size: 17px;")
        label_task.setFixedSize(100, 30)       
        
        label_asset_name = QLabel()
        label_asset_name.setText(asset_name)
        label_asset_name.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_asset_name.setObjectName("asset_name")
        label_asset_name.setStyleSheet("font-size: 17px;")
        label_asset_name.setFixedSize(100, 30)
        

        
        label_version = QLabel()
        label_version.setText(version)
        label_version.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_version.setObjectName("version")
        label_version.setStyleSheet("font-size: 17px;")
        label_version.setFixedSize(90, 30)


        label_ext = QLabel()
        label_ext.setText(ext)
        label_ext.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_ext.setObjectName("ext")
        label_ext.setStyleSheet("font-size: 17px;")
        label_ext.setFixedSize(90, 30)       
        
        
        label_path = QLabel()
        label_path.setText(path)
        label_path.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        label_path.setObjectName("path")
        label_path.setStyleSheet("font-size: 11px;")
        label_path.setFixedSize(500, 30)       
        
        grid_layout = QGridLayout()
        
        
        grid_layout.addWidget(label_icon_image, 0, 0)
        grid_layout.addWidget(label_task, 0, 1)
        grid_layout.addWidget(label_asset_name, 0, 2)
        grid_layout.addWidget(label_version, 0, 3)
        grid_layout.addWidget(label_ext, 0, 4)
        grid_layout.addWidget(label_path, 1, 1)
        

        container_widget = QWidget()
        container_widget.setLayout(grid_layout)

        self.ui.tableWidget.setCellWidget(row_idx, 0, container_widget)



if __name__ == "__main__":
    if not QApplication.instance():
        app = QApplication(sys.argv)
    win = AssetUpload()
    win.show()
    app.exec()