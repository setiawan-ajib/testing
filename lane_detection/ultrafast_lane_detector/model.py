import torch
# from line_detection_ufld.ultrafastLaneDetector.backbone import resnet
from lane_detection.ultrafast_lane_detector.backbone import resnet
import numpy as np
class parsingNet(torch.nn.Module):
    def __init__(self, size=(288, 800), pretrained=True, backbone='50', cls_dim=(37, 10, 4), use_aux=False):
        super(parsingNet, self).__init__()

        self.size = size
        self.w = size[0]
        self.h = size[1]
        self.cls_dim = cls_dim 
        self.total_dim = np.prod(cls_dim)

        self.model = resnet(backbone, pretrained=pretrained)

        self.cls = torch.nn.Sequential(
            torch.nn.Linear(1800, 2048),
            torch.nn.ReLU(),
            torch.nn.Linear(2048, self.total_dim),
        )

        self.pool = torch.nn.Conv2d(512,8,1) if backbone in ['34','18'] else torch.nn.Conv2d(2048,8,1)

    def forward(self, x):
        x2,x3,fea = self.model(x)

        fea = self.pool(fea).view(-1, 1800)

        group_cls = self.cls(fea).view(-1, *self.cls_dim)

        return group_cls