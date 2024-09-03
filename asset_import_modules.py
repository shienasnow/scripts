import os
import maya.cmds as cmds


def import_reference_file(asset_path):
    """
    애셋의 경로를 입력받으면 레퍼런스로 임포트하는 메서드입니다.
    마야 특징을 따라 네임 스페이스는 파일의 이름으로 생성합니다.
    """
    file_name = os.path.basename(asset_path)
    name_space = file_name.split(".")[0]

    try:
        reference_node = cmds.file(asset_path, reference=True, namespace=name_space)
        return reference_node
    except:
        return None


def get_reference_assets():
    """
    레퍼런스 노드들의 애셋 이름과 파일 경로를 딕셔너리로 리턴합니다.
    """
    reference_dict = {}
    ref_assets = cmds.ls(type="reference")
    for ref in ref_assets:
        if ref == 'sharedReferenceNode':
            continue
        tmp = {}
        node_name = cmds.referenceQuery(ref, nodes=True, dagPath=True)[0]
        reference_file_path = cmds.referenceQuery(ref, filename=True)
        if ":" in node_name:
            asset_name = node_name.split(":")[-1]
        else:
            asset_name = node_name
        tmp["asset_name"] = asset_name
        tmp["reference_file_path"] = reference_file_path
        tmp["version"] = reference_file_path.split("/")[-2] # v002
        reference_dict[ref] = tmp

    return reference_dict


def update_reference_file_path(ref_node, new_path):
    """
    레퍼런스 노드와 새로운 경로를 주면 레퍼런스 노드의 파일 경로를 업데이트 합니다.
    """
    if not os.path.exists(new_path):
        print ("경로에 파일이 존재하지 않습니다. 레퍼런스 노드를 업데이트 할 수 없습니다.")
        return None
    cmds.file(new_path, loadReference=ref_node)
    return ref_node


def set_render_resolution(undistortion_height, undistortion_width):

    cmds.setAttr("defaultResolution.width", int(undistortion_width))
    cmds.setAttr("defaultResolution.height", int(undistortion_height))


def set_frame_range(start_frame, end_frame):

    # 타임 슬라이더의 시작 및 종료 프레임 설정
    cmds.playbackOptions(min=start_frame, max=end_frame)

    # 현재 프레임 범위도 동일하게 설정 (프레임 범위 안에서 현재 시작 및 종료 프레임 설정)
    cmds.playbackOptions(ast=start_frame, aet=end_frame)