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

class AssetPublish(QWidget):
    def __init__(self):
        super().__init__()

        self.make_ui()

        self.get_current_file_path()
        self.classify_task()
        self.get_asset_name()
        self.get_version()

        self.ui.pushButton_pub.clicked.connect(self.get_root_nodes)

    def make_ui(self):
        my_path = os.path.dirname(__file__)
        ui_file_path = my_path +"/asset_publish.ui"

        ui_file = QFile(ui_file_path)
        ui_file.open(QFile.ReadOnly) # 이거 꼭 있어야 합니다
        loader = QUiLoader()
        self.ui = loader.load(ui_file, self)
        ui_file.close()

    def get_current_file_path(self): # 현재 작업 파일의 경로 가져오기
        self.current_file_path = cmds.file(query=True, sceneName=True)
        # /home/rapa/wip/Moomins/asset/Prop/coffee cup/lkd/wip/scenes/v001/glass_v001_w001.mb



# 현재 경로에서 task 가져와서 task에 따라 클린업 리스트 다르게 표시
# Publish 버튼 누르면 Task마다 다른 정보 Export, SG에 status 업데이트
    def classify_task(self):
        split_file_path = self.current_file_path.split("/")
        user_task = split_file_path[8]

        if user_task == "mod": # publish mb
            mod_clean_up_list = """
            - Modeling CleanUp List -

            <지오메트리 최적화>
            - 불필요한 폴리곤 제거
            - N-gons와 트라이앵글 정리
            - 에지 플로우 개선
            
            <토폴로지 정리>
            - 심(seam) 위치 최적화
            - 버텍스 웰딩(welding) 확인
            - 중복 버텍스 제거
            
            <네이밍 및 구조화>
            - 일관된 네이밍 규칙 적용
            - 논리적인 오브젝트 그룹화
            - 불필요한 그룹 및 레이어 정리
            
            <히스토리 및 변형>
            - 모델링 히스토리 삭제
            - 프리즈 트랜스폼 적용
            - 피벗 포인트 중심 정렬
        """
            self.ui.textEdit_comment.setText(mod_clean_up_list)

            self.ui.pushButton_pub.clicked.connect(self.export_mb)
            self.ui.pushButton_pub.clicked.connect(self.open_folder)
            self.ui.pushButton_pub.clicked.connect(self.sg_status_update)

        elif user_task == "lkd": # publish mb, scenes/shader/shader.ma, sourceimages/texture.tiff
            lkd_clean_up_list = """
            - LookDev CleanUp List -
            
            <텍스처 맵 최적화>
            - 텍스처 해상도 표준화
            - 불필요한 알파 채널 제거
            - 파일 포맷 최적화 (예: PNG, TGA)
            
            <UV 레이아웃 확인>
            - UV 공간 활용도 검토
            - 텍셀 밀도 균일화
            - UV 아일랜드 간 블리딩(bleeding) 방지
            
            <머티리얼 설정>
            - 머티리얼 네이밍 규칙 적용
            - 불필요한 머티리얼 제거
            - 셰이더 네트워크 정리 및 최적화
            
            <텍스처 파일 관리>
            - 사용하지 않는 텍스처 파일 제거
            - 텍스처 파일 네이밍 규칙 적용
            - 텍스처 맵 종류별 구조화 (Diffuse, Normal, Specular 등)
            
            <퀄리티 체크>
            - 텍스처 타일링(tiling) 확인
            - 노멀 맵 방향 검증
            - 라이팅 환경에서의 텍스처 테스트
            """
            self.ui.textEdit_comment.setText(lkd_clean_up_list)

            self.ui.pushButton_pub.clicked.connect(self.export_mb)
            self.ui.pushButton_pub.clicked.connect(self.export_shader_ma)
            self.ui.pushButton_pub.clicked.connect(self.open_folder)
            # self.ui.pushButton_pub.clicked.connect(self.export_texture)
            self.ui.pushButton_pub.clicked.connect(self.sg_status_update)

        elif user_task == "rig": # publish mb
            rig_clean_up_list = """
            - Rigging CleanUp List -
            
            <리그 구조 최적화>
            - 조인트 계층 구조 확인
            - 컨트롤러 정리 및 최적화
            - 제약 조건(Constraints) 검토
            
            <네이밍 및 조직화>
            - 일관된 네이밍 규칙 적용
            - 논리적 그룹화 및 계층 구조 정리
            
            <스키닝 및 디포메이션 개선>
            - 스키닝 품질 확인 및 웨이트 페인팅 조정
            - 디포머 최적화
            
            <성능 및 애니메이션 테스트>
            - 불필요한 히스토리 및 노드 제거
            - 기본 포즈, 극단적 포즈, 사이클 애니메이션 테스트
            
            <마무리 및 문서화>
            - 커스텀 속성 정리 및 디스플레이 레이어 설정
            - 리그 사용 설명서 작성 및 특이사항 기록
            """
            self.ui.textEdit_comment.setText(rig_clean_up_list)

            self.ui.pushButton_pub.clicked.connect(self.export_mb)
            self.ui.pushButton_pub.clicked.connect(self.open_folder)
            self.ui.pushButton_pub.clicked.connect(self.sg_status_update)

    def get_asset_name(self): # 현재 경로에서 asset name 가져와서 라벨에 표시

        split_file_path = self.current_file_path.split("/")
        self.asset_name = split_file_path[7]
        self.ui.label_assetname.setText(self.asset_name)

    def get_version(self): # 현재 경로에서 버전 가져와서 라벨에 표시

        split_file_path = self.current_file_path.split("/")
        file_name = split_file_path[11]
        p = re.compile('v\d{3}')
        p_data = p.search(file_name) #객체화
        version = p_data.group()
        self.ui.label_version.setText(version)



### Publish 버튼 누르면 Export
# 폴더 생성
    def make_publish_path(self): # pub 경로 생성
        if not self.current_file_path: # 현재 작업 파일 경로가 없을 경우
            print("파일이 저장되지 않았거나 열리지 않았습니다.")
            QMessageBox.about(self, "경고", "파일이 저장되지 않았거나 열리지 않았습니다.")

        split_file_path = self.current_file_path.split("/")
        project = split_file_path[4] # Moomins
        asset_type = split_file_path[6] # prop
        asset_name = split_file_path[7] # coffee cup
        task = split_file_path[8] # lkd

        file_name = split_file_path[-1]
        p = re.compile('v\d{3}')
        p_data = p.search(file_name)    
        version = p_data.group() # v001

        # Publish 경로에 (cache/scenes/images/sourceimages) 4개 폴더 생성되어야함
        self.open_pub_path=f"/home/rapa/pub/{project}/asset/{asset_type}/{asset_name}/{task}/pub/"
        # /home/rapa/pub/Moomins/asset/prop/cup/lkd/pub/
        folder_list =['cache', 'scenes', 'images', 'sourceimages']

        for folder in folder_list:
            folder_path = os.path.join(self.open_pub_path, folder, version)
            os.makedirs(folder_path, exist_ok=True) # 폴더 생성
        print (f"경로 '{folder_path}가 성공적으로 생성되었습니다.")

    def make_publish_lkd_path(self): # lkd에서만 scenes/shader 폴더 생성
        if not self.current_file_path: # 현재 작업 파일 경로가 없을 경우
            print("파일이 저장되지 않았거나 열리지 않았습니다.")
            QMessageBox.about(self, "경고", "파일이 저장되지 않았거나 열리지 않았습니다.")

        split_file_path = self.current_file_path.split("/")
        project = split_file_path[4] # Moomins
        asset_type = split_file_path[6] # prop
        asset_name = split_file_path[7] # cup
        task = split_file_path[8] # lkd

        file_name = split_file_path[-1]
        p = re.compile('v\d{3}')
        p_data = p.search(file_name)
        version = p_data.group() # v001

        lkd_pub_path = f"/home/rapa/pub/{project}/asset/{asset_type}/{asset_name}/{task}/pub/scenes/{version}/shader/"
        os.makedirs(lkd_pub_path, exist_ok=True) # 폴더 생성
        print (f"경로 '{lkd_pub_path}가 성공적으로 생성되었습니다.")
        
        return lkd_pub_path

    def open_folder(self): # 생성된 폴더 오픈
        subprocess.call(["xdg-open", self.open_pub_path])

# Export
    def get_root_nodes(self): # 최상위의 그룹 이름을 root_nodes 리스트로 리턴
        """
        씬의 최상위 노드를 찾아서 root_nodes 리스트에 넣는다
        """
        all_objects = cmds.ls(dag=True, long=True) # 씬의 모든 노드를 가져옴

        root_nodes = []
        # 모든 오브젝트를 반복하면서 최상위 노드를 찾습니다.
        for obj in all_objects:
            parent = cmds.listRelatives(obj, parent=True) # 현재 오브젝트의 부모를 가져옵니다.
            if parent is None: # 부모가 없으면 최상위 노드로 간주합니다.
                root_nodes.append(obj)
        return root_nodes

    def export_mb(self):
        """
        현재 선택된 객체 또는 씬을 Maya Binary 파일(.mb)로 내보냅니다.
        :param file_path: 내보낼 .mb 파일의 전체 경로
        네임스페이스 없애기
        """
        self.make_publish_path() # 폴더 생성

        self.pub_path = self.current_file_path.replace("/wip/", "/pub/")
        # /home/rapa/pub/Moomins/asset/prop/cup/lkd/pub/scenes/v001/shader//cup_v001_w001.mb.ma

        # 현재 파일을 mb로 export
        cmds.file(self.pub_path, exportAll=True, type="mayaBinary", force=True)

    def export_shader_ma(self): # scenes/shader/shader.ma
        """
        선택된 파일을 ma로 내보냅니다. 근데 파일이 아니라 shader만 내보내야 하는지?
        texture image는 어떻게 따로 보내지?
        """
        self.make_publish_path() #폴더 생성
        self.make_publish_lkd_path() # scenes 안에 shader 폴더 생성

        lkd_path = self.make_publish_lkd_path()
        current_file_name = os.path.basename(cmds.file(query=True, sceneName=True))

        shader_pub_path = f"{lkd_path}/{current_file_name}.ma"
        print(shader_pub_path) # /home/rapa/pub/Moomins/asset/prop/cup/lkd/pub/scenes/v001/shader/

        # 노드 선택
        cmds.select(clear=True) # 선택된 노드들 클리어
        root_nodes = self.get_root_nodes()
        for root_node in root_nodes:
            cmds.select(root_node, add=True) # 모든 root node 선택

        # ma로 Export
        cmds.file(shader_pub_path, force=True, options="v=0", type="mayaAscii", exportSelected=True)



    def export_texture(self): # sourceimages/texture.tiff
        pass




# Backend (Shotgrid Status & Pub_File_Path Update)
    def sg_status_update(self):
        print("샷그리드에 pub 경로를 입력하고 stuatus를 업데이트합니다")
        # 업데이트 할 asset id 찾기
        self.asset_name


        # print(self.pub_path) # /home/rapa/pub/Moomins/asset/Prop/coffee cup/lkd/pub/scenes/v001/glass_v001_w001.mb/glass_v001.mb
        self.sg.update("Asset", asset_id, {"sg_status_list":"wip"}) # asset status 변경


        # Publish File Path 넣기
        self.sg.update("Asset", asset_id, {"description": self.pub_path}) # asset description 변경

    # publish에서는 fin으로 바꾸기
    # shot publish의 경우에는 camera의 undistortion size도 업데이트 해주기
    # frame range




if __name__ == "__main__":
    if not QApplication.instance():
        app = QApplication(sys.argv)
    win = AssetPublish()
    win.show()
    app.exec()