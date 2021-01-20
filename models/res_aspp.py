#ResNet50 + ASPP

import torch.nn as nn
import math
import torch
import numpy as np
import torch.nn.functional as F
from collections import OrderedDict
import torchvision.models as models

affine_par = True # allow weights and bias in batch normalization layers or not
learnable_bn_weights = False # allow learnable weights and bias in batch normalization layers or not


def conv3x3(in_planes, out_planes, stride=1):
    "3x3 convolution with padding"
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                     padding=1, bias=False)


class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(BasicBlock, self).__init__()
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = nn.BatchNorm2d(planes, affine = affine_par)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = nn.BatchNorm2d(planes, affine = affine_par)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out


class Bottleneck(nn.Module):
    expansion = 4

    def __init__(self, inplanes, planes, stride=1,  dilation_ = 1, downsample=None):
        super(Bottleneck, self).__init__()
        self.conv1 = nn.Conv2d(inplanes, planes, kernel_size=1, stride=stride, bias=False) # change
        self.bn1 = nn.BatchNorm2d(planes,affine = affine_par)
        if learnable_bn_weights == False:
            for i in self.bn1.parameters():
                i.requires_grad = False
        padding = 1
        if dilation_ == 2:
            padding = 2
        elif dilation_ == 4:
            padding = 4
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=1, # change
                               padding=padding, bias=False, dilation = dilation_)
        self.bn2 = nn.BatchNorm2d(planes,affine = affine_par)
        if learnable_bn_weights == False:
            for i in self.bn2.parameters():
                i.requires_grad = False
        self.conv3 = nn.Conv2d(planes, planes * 4, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(planes * 4, affine = affine_par)
        if learnable_bn_weights == False:
            for i in self.bn3.parameters():
                i.requires_grad = False
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride



    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out

class Classifier_Module(nn.Module):

    def __init__(self,dilation_series,padding_series):
        super(Classifier_Module, self).__init__()
        self.conv2d_list = nn.ModuleList()
        for dilation,padding in zip(dilation_series,padding_series):
            self.conv2d_list.append(nn.Conv2d(2048,1,kernel_size=3,stride=1, padding =padding, dilation = dilation,bias = True))

        for m in self.conv2d_list:
            m.weight.data.normal_(0, 0.01)
        
        self.Sigmoid = nn.Sigmoid()

    def forward(self, x):
        out = self.conv2d_list[0](x)
        for i in range(len(self.conv2d_list)-1):
            out += self.conv2d_list[i+1](x)

        #add a sigmoid activation
        out = 10*self.Sigmoid(out)+0.01
        return out



class ResNet(nn.Module):
    def __init__(self, block, layers):
        self.inplanes = 64
        super(ResNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3,
                               bias=False)
        self.bn1 = nn.BatchNorm2d(64,affine = affine_par)
        if learnable_bn_weights == False:
            for i in self.bn1.parameters():
                i.requires_grad = False
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1, ceil_mode=True) # change
        self.layer1 = self._make_layer(block, 64, layers[0])
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2)
        self.layer3 = self._make_layer(block, 256, layers[2], stride=1, dilation__ = 2)
        self.layer4 = self._make_layer(block, 512, layers[3], stride=1, dilation__ = 4)
        self.layer5 = self._make_pred_layer(Classifier_Module, [6,12,18,24],[6,12,18,24]) # ASPP

    def _make_layer(self, block, planes, blocks, stride=1,dilation__ = 1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion or dilation__ == 2 or dilation__ == 4:
            downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, planes * block.expansion,
                          kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes * block.expansion,affine = affine_par),
            )
        if learnable_bn_weights == False:
            for i in downsample._modules['1'].parameters():
                i.requires_grad = False
        layers = []
        layers.append(block(self.inplanes, planes, stride,dilation_=dilation__, downsample = downsample ))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes,dilation_=dilation__))

        return nn.Sequential(*layers)

    def _make_pred_layer(self,block, dilation_series, padding_series):
        return block(dilation_series,padding_series)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.layer5(x)

        return x

class res50_aspp(nn.Module):
    def __init__(self, datasets ='kitti'):
        super(res50_aspp,self).__init__()
        self.Scale = ResNet(Bottleneck,[3, 4, 6, 3])

    def forward(self,x):
        input_size = x.size()[2:]  # x: [batch_size, 3, h, w]
        out = self.Scale(x)  # for original scale
        out = F.interpolate(out, size=input_size, mode='bilinear', align_corners=True)
        if self.training:
            return [out]
        else:
            return out

    # load pretrained resnet101 weights from torchvision resnet101 model
    def init_weights(self, use_pretrained_weights=False):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, 0.01)
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()
        if use_pretrained_weights:
            print("loading pretrained weights downloaded from pytorch.org")
            resnet50 = models.resnet50(pretrained=True)
            initial_state_dict = self.init_resnet50_params(resnet50)
            self.load_state_dict(initial_state_dict, strict=False)
        else:
            print("do not load pretrained weights for the monocular model")
    def init_resnet50_params(self, resnet50):
        initial_state_dict = resnet50.state_dict()
        new_state_dict = OrderedDict()
        for k, v in initial_state_dict.items():
            k = 'Scale.' + k
            new_state_dict[k] = v
        return new_state_dict
    # if you want to load from downloaded pretrained model:
    # model_path: path to the downloaded model
    # def init_resnet101_params(self, model_path):
    #     saved_state_dict = torch.load(model_path, map_location=lambda storage, loc: storage)
    #     new_state_dict = OrderedDict()
    #     for k, v in saved_state_dict.items():
    #         k = 'Scale.' + k
    #         new_state_dict[k] = v
#     return new_state_dict