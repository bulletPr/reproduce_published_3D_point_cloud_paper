
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
#      YUWEI CAO - 2020/10/22 9:29 AM
#
#


# ----------------------------------------
# import packages
# ----------------------------------------

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import itertools
from loss import ChamferLoss


# ----------------------------------------
# KNN
# ----------------------------------------

def knn(x, k):
    batch_size = x.size(0)
    num_points = x.size(2)

    inner = -2*torch.matmul(x.transpose(2,1),x)
    xx = torch.sum(x**2, dim=1, keepdim=True)
    pairwise_distance = -xx - inner - xx.transpose(2,1)

    idx = pairwise_distance.topk(k=k, dim=-1)[1] #(batch_size, num_points, k)

    if idx.get_device() == -1:
        idx_base = torch.arange(0, batch_size).view(-1,1,1)*num_points
    else:
        idx_base = torch.arange(0,batch_size,device=idx.get_device()).view(-1,1,1)*num_points
    idx = idx + idx_base
    idx = idx.view(-1)

    return idx

# ----------------------------------------
# Local Convolution
# ----------------------------------------


def local_cov(pts, idx):
    batch_size = pts.size(0)
    num_points = pts.size(2)
    pts = pts.view(batch_size, -1, num_points)              # (batch_size, 6, num_points)

    _, num_dims, _ = pts.size()

    x = pts.transpose(2, 1).contiguous()                    # (batch_size, num_points, 6)
    x = x.view(batch_size*num_points, -1)[idx, :]           # (batch_size*num_points*2, 6)
    x = x.view(batch_size, num_points, -1, num_dims)        # (batch_size, num_points, k, 6)

    x = torch.matmul(x[:,:,0].unsqueeze(3), x[:,:,1].unsqueeze(2))  # (batch_size, num_points, 6, 1) * (batch_size,
                                                                    # num_points, 1, 6) -> (batch_size, num_points, 6, 6)
    # x = torch.matmul(x[:,:,1:].transpose(3, 2), x[:,:,1:])
    # x = x.view(batch_size, num_points, 9).transpose(2, 1)   # (batch_size, 9, num_points)

    x = torch.cat((pts, x), dim=1)                          # (batch_size, 12, num_points)

    return x


# ----------------------------------------
# Local Maxpool
# ----------------------------------------

def local_maxpool(x, idx):
    batch_size = x.size(0)
    num_points = x.size(2)
    x = x.view(batch_size, -1, num_points)

    _, num_dims, _ = x.size()

    x = x.transpose(2, 1).contiguous()                      # (batch_size, num_points, num_dims)
    x = x.view(batch_size*num_points, -1)[idx, :]           # (batch_size*n, num_dims) -> (batch_size*n*k, num_dims)
    x = x.view(batch_size, num_points, -1, num_dims)        # (batch_size, num_points, k, num_dims)
    x, _ = torch.max(x, dim=2)                              # (batch_size, num_points, num_dims)

    return x


# ----------------------------------------
# Local Maxpool
# ----------------------------------------

def get_graph_feature(x, k=20, idx=None):
    batch_size = x.size(0)
    num_points = x.size(2)
    x = x.view(batch_size, -1, num_points)      # (batch_size, num_dims, num_points)
    if idx is None:
        idx = knn(x, k=k)                       # (batch_size, num_points, k)

    _, num_dims, _ = x.size()

    x = x.transpose(2, 1).contiguous()          # (batch_size, num_points, num_dims)
    feature = x.view(batch_size*num_points, -1)[idx, :]                 # (batch_size*n, num_dims) -> (batch_size*n*k, num_dims)
    feature = feature.view(batch_size, num_points, k, num_dims)         # (batch_size, num_points, k, num_dims)
    x = x.view(batch_size, num_points, 1, num_dims).repeat(1, 1, k, 1)  # (batch_size, num_points, k, num_dims)

    feature = torch.cat((feature-x, x), dim=3).permute(0, 3, 1, 2)      # (batch_size, num_points, k, 2*num_dims) -> (batch_size, 2*num_dims, num_points, k)

    return feature                              # (batch_size, 2*num_dims, num_points, k)


# ----------------------------------------
# Encoder
# ----------------------------------------

class FoldNet_Encoder(nn.Module):
    def __init__(self, args):
        super(FoldNet_Encoder, self).__init__()
        if args.k == None:
            self.k = 16
        else:
            self.k = args.k
        self.n = 2048 # input point cloud size
        self.mlp1 = nn.Sequential(
                nn.Conv1d(6,64,1),
                nn.ReLU(),
                nn.Conv1d(64,64,1),
                nn.ReLU(),
                nn.Conv1d(64,64,1),
                nn.ReLU(),
        )

        self.linear1 = nn.Linear(64,64)
        self.conv1 = nn.Conv1d(64,128,1)
        self.linear2 = nn.Linear(128,128)
        self.conv2 = nn.Conv1d(128,1024,1)
        self.mlp2 = nn.Sequential(
               nn.Conv1d(1024, args.feat_dims, 1),
               nn.ReLU(),
               nn.Conv1d(args.feat_dims, args.feat_dims, 1),
        )

    def graph_layer(self, x, idx):
        x = local_maxpool(x, idx)
        x = self.linear1(x)
        x = x.transpose(2,1)
        x = F.relu(self.conv1(x))
        x = local_maxpool(x, idx)
        x = self.linear2(x)
        x = x.transpose(2,1)
        x = self.conv2(x)
        return x

    def forward(self, pts):
        pts = pts.transpose(2,1) #(batch_size, 6, num_points)
        idx = knn(pts, k=self.k)
        x = local_cov(pts, idx) #(batch_size, 6, num_points) -> (batch_size, 12, num_points)
        x = self.mlp1(x) #(batch_size, 64, num_points)
        x = self.graph_layer(x, idx) #(batch_size,1024, num_points)
        x = torch.max(x, 2, keepdim=True)[0] #(batch_size,1024,1)
        x = self.mlp2(x)                     #(batch_size, feat_dims,1)
        feat = x.transpose(2,1)              #(batch_size,1,feat_dims)
        return feat

    class FoldNet_Decoder(nn.Module):
        def __init__(self, args):
            super(FoldNet_Decoder, self).__init__()
            self.m = 2025
            self.shape = args.shape
            self.meshgrid=[[-0.3,0.3,45], [-0.3,-0.3,45]]
            self.fold1 = nn.Sequential(
                    nn.Conv1d(args.feat_dims+2, args.feat_dims, 1),
                    nn.ReLU(),
                    nn.Conv1d(args.feat_dims, args.feat_dims, 1),
                    nn.ReLU(),
                    nn.Conv1d(args.feat_dims, 3, 1),
            )

            self.fold2 = nn.Sequential(
                    nn.Conv1d(args.feat_dims+3, args.feat_dims, 1),
                    nn.ReLU(),
                    nn.Conv1d(args.feat_dims, args.feat_dims,1),
                    nn.ReLU(),
                    nn.Conv1d(args.feat_dims,3,1),
            )


        def build_grid(self, batch_size):
            x = np.linspace(*self.meshgrid[0])
            y = np.linspace(*self.meshgrid[1])
            grid = np.array(list(itertools.product(x, y)))
            grid = np.repeat(grid[np.newaxis, ...], repeats=batch_size, axis=0)
            grid = torch.tensor(grid)
            return grid.float()


        def forward(self, input):
            input = input.transpose(1,2).repeat(1,1,self.m) #(batch_size,feat_dims,num_points)
            grid = self.build_grid(x.shape[0]).transpose(1,2) #(bs, 2, feat_dims)
            if x.get_device() != -1:
                grid = grid.cuda(x.get_device())
            concate1 = torch.cat((input, grid),dim=1) #(bs, feat_dims+2, num_points)
            after_fold1 = self.fold1(concate1) #(bs,3,num_points)
            concate2 = torch.cat((x, after_fold1), dim=1) #(bs, feat_dims+3, num_points)
            after_fold2 = self.fold2(concate2) #(bs, 3, num_points)
            return after_fold2.transpose(1,2)


    Class FoldNet(nn.Module):
