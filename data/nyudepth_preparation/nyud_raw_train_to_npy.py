import os
import shutil
from oct2py import octave
from PIL import Image
import numpy as np
import scipy.ndimage

MAX_DEPTH = 10


def save_npy(source_dir, target_dir):
    image_folder = os.path.join(source_dir, '_rgb')
    depth_folder = os.path.join(source_dir, '_depth')
    mask_folder = os.path.join(source_dir, '_mask')
    npy_folder = os.path.join(target_dir, 'npy')
    
    # dangerous removal
    if os.path.isdir(npy_folder):
        shutil.rmtree(npy_folder)

    os.makedirs(npy_folder)
    image_paths = [os.path.join(image_folder, n)
                   for n in sorted(os.listdir(image_folder))]
    depth_paths = [os.path.join(depth_folder, n)
                   for n in sorted(os.listdir(depth_folder))]
    mask_paths = [os.path.join(mask_folder, n)
                  for n in sorted(os.listdir(mask_folder))]
    for i, paths in enumerate(zip(image_paths, depth_paths, mask_paths)):
        image_path, depth_path, mask_path = paths
        image = np.array(Image.open(image_path), dtype=np.float32)
        depth_0 = np.array(Image.open(depth_path), dtype=np.float32)
        depth_0 = np.expand_dims(depth_0 , 2)
        depth_0 = (depth_0 / 2 ** 16) * MAX_DEPTH
        #print(np.max(depth_0))
        depth_1 = np.array(Image.open(mask_path), dtype=np.float32)
        depth_1 = np.float32((np.expand_dims(depth_1, 2) / 255) > 0.5)
        #print(np.min(depth_1))
        stacked = np.transpose(np.concatenate((image, depth_0, depth_1), 2),
                               (2, 0, 1))
        # original image size after matlab crop is (427, 561) and this crop is from mask(45:471, 41:601) = 1 
        # after the interpolation the size is (292,384)

        # stacked = scipy.ndimage.interpolation.zoom(stacked, (1, 384/561, 384/561), order=1)# turn image into resolution by (292,384)
        stacked = scipy.ndimage.interpolation.zoom(stacked, (1, 320/480, 448/640), order=1)# turn image into resolution by (284,392) than crop into (256,352)

        np.save(os.path.join(npy_folder, '{}.npy'.format(i)), stacked)


if __name__ == '__main__':
    save_npy('/srv/glusterfs/zfang/a',# wait to change
             '/srv/glusterfs/zfang/nyu_depth_v2_other_resolution')
