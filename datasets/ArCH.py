#
#
#      0=================================0
#      |    Project Name                 |
#      0=================================0
#
#
# ----------------------------------------------------------------------------------------------------------------------
#
#      Implements read ArchDatase
#
# ----------------------------------------------------------------------------------------------------------------------
#
#      YUWEI CAO - 2020/10/2
#
#
from torch.utils.data.dataset import Dataset
import os
import numpy as np
import os.path
import torch
import sys
from datetime import datetime
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(ROOT_DIR, 'utils'))
from pc_utils import translate_pointcloud, jitter_pointcloud, rotate_pointcloud
from pc_utils import load_seg
DATA_DIR = os.path.join(ROOT_DIR, 'data')


#ArCH dataset load
class ArchDataset(Dataset):
    def __init__(self, filelist, num_points=2048, random_translate=False, random_rotate=False,
            random_jitter=False):
        self.random_translate = random_translate
        self.random_jitter = random_jitter
        self.random_rotate = random_rotate
        
        #define all train/test file
        self.path_h5py_all = filelist

        # acquire split file dir
        log_string("check paths length:" + str(self.path_h5py_all))
        
        log_string("Read datasets by load .h5 files")
        self.data, _, self.num_points, self.labels, _ = load_seg(self.path_h5py_all)
        log_string("size of all point_set: [" + str(self.data.shape) + "," + str(self.labels.shape) + "]")


    def __getitem__(self, index):
        
        point_set = self.data[index]
        label = self.labels[index]

        # data augument
        if self.random_translate:
            point_set = translate_pointcloud(point_set[:,0:3])
        if self.random_jitter:
            point_set = jitter_pointcloud(point_set[:,0:3])
        if self.random_rotate:
            point_set = rotate_pointcloud(point_set[:,0:3])

        #conver numpy array to pytorch Tensor
        point_set = torch.from_numpy(point_set)
        #colors = torch.from_numpy()
        label = torch.from_numpy(np.array([label]).astype(np.int8))
        label = label.squeeze(0)
        log_string("read point_set: [" + str(index) + "]")
        log_string("point_set size: [" + str(point_set.shape) + "," + str(label.shape) + "]")
        return point_set, label


    def __len__(self):
        return self.data.shape[0]


LOG_FOUT = open(os.path.join(ROOT_DIR, 'LOG','datareadlog.txt'), 'w')
def log_string(out_str):
    LOG_FOUT.write(out_str + '\n')
    LOG_FOUT.flush()
    print(out_str)


    '''
        if split == 'train':
            self.filelist = os.path.join(self.root, 'train_data_files.txt') 
            # Read filelist
            print('{}-Preparing datasets...'.format(datetime.now()))
            is_list_of_h5_list = not is_h5_list(self.filelist)
            if is_list_of_h5_list:
                seg_list = load_seg_list(self.filelist)
                print("segmentation files:" + str(len(seg_list)))
                seg_list_idx = 0
                self.path_txt_all = seg_list[seg_list_idx]
                seg_list_idx = seg_list_idx + 1
            else:
                self.path_txt_all = self.filelist
        else:
            self.path_txt_all = os.path.join(self.root, 'test_data_files.txt')
    '''