import cv2
import torch
import scipy.special
import numpy as np
import torchvision.transforms as transforms
from PIL import Image
# from line_detection_ufld.ultrafastLaneDetector.model import parsingNet
from lane_detection.ultrafast_lane_detector.model import parsingNet

tusimple_row_anchor = [ 64,  68,  72,  76,  80,  84,  88,  92,  96, 100, 104, 108, 112,
			116, 120, 124, 128, 132, 136, 140, 144, 148, 152, 156, 160, 164,
			168, 172, 176, 180, 184, 188, 192, 196, 200, 204, 208, 212, 216,
			220, 224, 228, 232, 236, 240, 244, 248, 252, 256, 260, 264, 268,
			272, 276, 280, 284]
class ModelConfig():
	def __init__(self):
		self.img_w = 1280
		self.img_h = 720
		self.row_anchor = tusimple_row_anchor
		self.griding_num = 100
		self.cls_num_per_lane = 56

class UltrafastLaneDetector():
	def __init__(self, model_path, use_gpu=False):
		self.use_gpu = use_gpu
		self.cfg = ModelConfig()
		self.model = self.initialize_model(model_path, self.cfg, use_gpu)
		self.img_transform = self.initialize_image_transform()

	@staticmethod
	def initialize_model(model_path, cfg, use_gpu):
		net = parsingNet(pretrained = False, backbone='18', cls_dim = (cfg.griding_num+1,cfg.cls_num_per_lane,4),
						use_aux=False)

		if use_gpu:
			net = net.cuda()
			state_dict = torch.load(model_path, map_location='cuda')['model'] # CUDA
		else:
			state_dict = torch.load(model_path, map_location='cpu')['model'] # CPU

		compatible_state_dict = {}
		for k, v in state_dict.items():
			if 'module.' in k:
				compatible_state_dict[k[7:]] = v
			else:
				compatible_state_dict[k] = v

		net.load_state_dict(compatible_state_dict, strict=False)
		net.eval()

		return net

	@staticmethod
	def initialize_image_transform():
		img_transforms = transforms.Compose([
			transforms.Resize((288, 800)),
			transforms.ToTensor(),
			transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
		])

		return img_transforms

	# def detect_lanes(self, image):

	# 	input_tensor = self.prepare_input(image)
	# 	output = self.inference(input_tensor)
	# 	lanes_points, lanes_detected = self.process_output(output, self.cfg)

	# 	return lanes_points, lanes_detected

	def detect_lanes(self, image):
		orig_h, orig_w = image.shape[:2]

		input_tensor = self.prepare_input(image)
		output = self.inference(input_tensor)
		lanes_points, lanes_detected = self.process_output(output, self.cfg)

		scale_x = orig_w / self.cfg.img_w
		scale_y = orig_h / self.cfg.img_h

		lanes_points = [
			[[int(x * scale_x), int(y * scale_y)] for x, y in lane]
			for lane in lanes_points
		]

		return lanes_points, lanes_detected

	def prepare_input(self, img):
		img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
		img_pil = Image.fromarray(img)
		input_img = self.img_transform(img_pil)
		input_tensor = input_img[None, ...]

		if self.use_gpu:
			input_tensor = input_tensor.cuda()

		return input_tensor

	def inference(self, input_tensor):
		with torch.no_grad():
			output = self.model(input_tensor)

		return output

	@staticmethod
	def process_output(output, cfg):		
		processed_output = output[0].data.cpu().numpy()
		processed_output = processed_output[:, ::-1, :]
		prob = scipy.special.softmax(processed_output[:-1, :, :], axis=0)
		idx = np.arange(cfg.griding_num) + 1
		idx = idx.reshape(-1, 1, 1)
		loc = np.sum(prob * idx, axis=0)
		processed_output = np.argmax(processed_output, axis=0)
		loc[processed_output == cfg.griding_num] = 0
		processed_output = loc

		col_sample = np.linspace(0, 800 - 1, cfg.griding_num)
		col_sample_w = col_sample[1] - col_sample[0]

		lanes_points = []
		lanes_detected = []

		max_lanes = processed_output.shape[1]
		for lane_num in range(max_lanes):
			lane_points = []
			if np.sum(processed_output[:, lane_num] != 0) > 2:

				lanes_detected.append(True)

				for point_num in range(processed_output.shape[0]):
					if processed_output[point_num, lane_num] > 0:
						lane_point = [int(processed_output[point_num, lane_num] * col_sample_w * cfg.img_w / 800) - 1, int(cfg.img_h * (cfg.row_anchor[cfg.cls_num_per_lane-1-point_num]/288)) - 1 ]
						lane_points.append(lane_point)
			else:
				lanes_detected.append(False)

			lanes_points.append(lane_points)
		return lanes_points, lanes_detected