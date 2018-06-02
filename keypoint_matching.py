# Open3Dを使った6DoF推定

from open3d import *
import numpy as np
import copy

#sourceをtransformationによって剛体変換してtargetと一緒に表示
def draw_registration_result(source, target, transformation):
    source_temp = copy.deepcopy(source)
    target_temp = copy.deepcopy(target)
    source_temp.paint_uniform_color([1, 0.706, 0])
    target_temp.paint_uniform_color([0, 0.651, 0.929])
    source_temp.transform(transformation)
    draw_geometries([source_temp, target_temp])

#キーポイント検出，法線推定，特徴記述
def preprocess_point_cloud(pcd, voxel_size):
    print(":: Downsample with a voxel size %.3f." % voxel_size)
    pcd_kp = voxel_down_sample(pcd, voxel_size)

    radius_normal = voxel_size * 2
    viewpoint = np.array([0.,0.,100.], dtype='float64')
    estimate_normals(pcd_kp, KDTreeSearchParamHybrid(radius = radius_normal, max_nn = 30))
    orient_normals_towards_camera_location( pcd_kp, camera_location = viewpoint )        

    radius_feature = voxel_size * 5
    print(":: Compute FPFH feature with search radius %.3f." % radius_feature)
    pcd_fpfh = compute_fpfh_feature(pcd_kp,
            KDTreeSearchParamHybrid(radius = radius_feature, max_nn = 100))
    return pcd_kp, pcd_fpfh

#RANSACによるレジストレーション
def execute_global_registration(
        source_kp, target_kp, source_fpfh, target_fpfh, voxel_size):
    distance_threshold = voxel_size * 1.5
    print(":: RANSAC registration on downsampled point clouds.")
    print("   Since the downsampling voxel size is %.3f," % voxel_size)
    print("   we use a liberal distance threshold %.3f." % distance_threshold)
    result = registration_ransac_based_on_feature_matching(
            source_kp, target_kp, source_fpfh, target_fpfh,
            distance_threshold,
            TransformationEstimationPointToPoint(False), 4,
            [CorrespondenceCheckerBasedOnEdgeLength(0.9),
            CorrespondenceCheckerBasedOnDistance(distance_threshold)],
            RANSACConvergenceCriteria(40000, 500))
    return result

#ICPによるリファイン
def refine_registration(source, target, source_fpfh, target_fpfh, voxel_size):
    distance_threshold = voxel_size * 0.4
    print(":: Point-to-plane ICP registration is applied on original point")
    print("   clouds to refine the alignment. This time we use a strict")
    print("   distance threshold %.3f." % distance_threshold)
    result = registration_icp(source, target, distance_threshold,
            result_ransac.transformation,
            TransformationEstimationPointToPlane())
    return result

if __name__ == "__main__":
    #データ読み込み
    print(":: Load two point clouds to be matched.")
    source = read_point_cloud("bun.pcd")
    target = read_point_cloud("bun045.pcd")
    draw_registration_result(source, target, np.identity(4))

    #キーポイント検出と特徴量抽出
    voxel_size = 0.01
    source_kp, source_fpfh = preprocess_point_cloud(source, voxel_size)
    target_kp, target_fpfh = preprocess_point_cloud(target, voxel_size)

    #RANSACによる姿勢推定
    result_ransac = execute_global_registration(source_kp, target_kp,
            source_fpfh, target_fpfh, voxel_size)

    print(result_ransac)
    draw_registration_result(source_kp, target_kp, result_ransac.transformation)

    #ICPによる微修正
    result_icp = refine_registration(source, target,
            source_fpfh, target_fpfh, voxel_size)
    print(result_icp)
    draw_registration_result(source, target, result_icp.transformation)