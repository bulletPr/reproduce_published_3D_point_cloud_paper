
#
#
#      0=================================0
#      |    Project Name                 |
#      0=================================0
#
#
# ----------------------------------------------------------------------------------------------------------------------
#
#      Implements
#
# ----------------------------------------------------------------------------------------------------------------------
#
#      YUWEI CAO - 2020/10/21 5:26 PM 
#
#
import torch
from ArCH import ArchDataset
from ShapeNetCore import Dataset
import os.path
import sys
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)
DATA_DIR = os.path.join(ROOT_DIR, 'data')

sys.path.append(os.path.join(ROOT_DIR, 'utils'))
from pc_utils import is_h5_list, load_seg_list

def get_dataloader(filelist, batch_size=32,  
        num_points=2048, num_workers=4, group_shuffle=False, shuffle=False, random_translate=False, random_rotate=False,
            random_jitter=False, drop_last=False):
    dataset = ArchDataset(
            filelist=filelist,
            num_points=num_points,
            group_shuffle=group_shuffle,
            random_translate=random_translate, 
            random_rotate=random_rotate,
            random_jitter=random_jitter)
    dataloader = torch.utils.data.DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            num_workers=num_workers,
            drop_last=drop_last)

    return dataloader

if __name__ == '__main__':
    filelist = os.path.join(DATA_DIR, 'arch', 'train_data_files.txt') 
    # Read filelist
    print('-Preparing datasets...')
    is_list_of_h5_list = not is_h5_list(filelist)
    if is_list_of_h5_list:
        seg_list = load_seg_list(filelist)
        print("segmentation files:" + str(len(seg_list)))
        seg_list_idx = 0
        filepath = seg_list[seg_list_idx]
        seg_list_idx = seg_list_idx + 1
    else:
        filepath = filelist
    dataloader = get_dataloader(filelist=filepath, batch_size=4, num_points=2048,group_shuffle=True,random_translate=False, random_rotate=False,
            random_jitter=False)
    print("dataloader size: ", dataloader.dataset.__len__())
    for iter, (pts,seg) in enumerate(dataloader):
        print("points: ", pts.shape, pts.type)
        print("segs: ", seg.shape, seg.type)
        break