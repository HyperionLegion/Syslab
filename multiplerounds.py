# import the necessary packages
import numpy as np
import argparse
import imutils
import time
import cv2
import os
import random
# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--input", required=True,
	help="path to input video")
ap.add_argument("-o", "--output", required=True,
	help="path to output video")
ap.add_argument("-y", "--yolo", required=True,
	help="base path to YOLO directory")
ap.add_argument("-c", "--confidence", type=float, default=0.5,
	help="minimum probability to filter weak detections")
ap.add_argument("-t", "--threshold", type=float, default=0.3,
	help="threshold when applyong non-maxima suppression")
args = vars(ap.parse_args())

# load the COCO class labels our YOLO model was trained on
labelsPath = os.path.sep.join([args["yolo"], "obj.names"])
LABELS = open(labelsPath).read().strip().split("\n")
# initialize a list of colors to represent each possible class label
np.random.seed(42)
COLORS = np.random.randint(0, 255, size=(len(LABELS), 3),
	dtype="uint8")
# derive the paths to the YOLO weights and model configuration
weightsPath = os.path.sep.join([args["yolo"], "yolo-obj_5100.weights"])
configPath = os.path.sep.join([args["yolo"], "yolo-obj.cfg"])
# load our YOLO object detector trained on COCO dataset (80 classes)
# and determine only the *output* layer names that we need from YOLO
print("[INFO] loading YOLO from disk...")
net = cv2.dnn.readNetFromDarknet(configPath, weightsPath)
ln = net.getLayerNames()
ln = [ln[i[0] - 1] for i in net.getUnconnectedOutLayers()]

# initialize the video stream, pointer to output video file, and
# frame dimensions
vs = cv2.VideoCapture(0) # replace with live stream
#vs = cv2.VideoCapture(args["input"])
writer = None
(W, H) = (None, None)
# try to determine the total number of frames in the video file
try:
	prop = cv2.cv.CV_CAP_PROP_FRAME_COUNT if imutils.is_cv2() \
		else cv2.CAP_PROP_FRAME_COUNT
	total = int(vs.get(prop))
	print("[INFO] {} total frames in video".format(total))
# an error occurred while trying to determine the total
# number of frames in the video file
except:
	print("[INFO] could not determine # of frames in video")
	print("[INFO] no approx. completion time can be provided")
	total = -1

cardToNum = {'A': 1,'J': 10, 'Q': 10, 'K': 10, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10}
for i in range(2,11):
	cardToNum[i] = i

cards_played = {}
for n in ['A', *range(2,11), 'J', 'Q', 'K']:
	for s in ['d', 'h', 's', 'c']:
		cards_played[str(n)+s] = 0

cards_seen = {}
# would look like {'5s': 5, '4d': 5, '6c': 6, etc. } to see how many frames in a row we have seen this card. only act when we confirm all cards have been seen at least 5 times.

cards = {"2s": 1, "3s": 1,"4s": 1,"5s": 1,"6s": 1,"7s": 1,"8s": 1,"9s": 1,"10s": 1,"Js": 1,"Qs": 1,"Ks": 1,"As": 1,
"2h": 1, "3h": 1,"4h": 1,"5h": 1,"6h": 1,"7h": 1,"8h": 1,"9h": 1,"10h": 1,"Jh": 1,"Qh": 1,"Kh": 1,"Ah": 1,
"2d": 1, "3d": 1,"4d": 1,"5d": 1,"6d": 1,"7d": 1,"8d": 1,"9d": 1,"10d": 1,"Jd": 1,"Qd": 1,"Kd": 1,"Ad": 1,
"2c": 1, "3c": 1,"4c": 1,"5c": 1,"6c": 1,"7c": 1,"8c": 1,"9c": 1,"10c": 1,"Jc": 1,"Qc": 1,"Kc": 1,"Ac": 1,}

dealer = 0
player = 0

curr_count = 0
add = {'2', '3', '4', '5', '6'}
subtract = {'A', '10', '9', '8', 'J', 'Q', 'K'}

# loop over frames from the video file stream
while True:
	# read the next frame from the file
	(grabbed, frame) = vs.read()
	print('read')
	# if the frame was not grabbed, then we have reached the end
	# of the stream

	if not grabbed:
		break
	# if the frame dimensions are empty, grab them
	frame = cv2.resize(frame, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
	if W is None or H is None:
		(H, W) = frame.shape[:2]
# construct a blob from the input frame and then perform a forward
	# pass of the YOLO object detector, giving us our bounding boxes
	# and associated probabilities
	blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (416, 416),
		swapRB=True, crop=False)
	net.setInput(blob)
	start = time.time()
	layerOutputs = net.forward(ln)
	end = time.time()

	# initialize our lists of detected bounding boxes, confidences,
	# and class IDs, respectively
	boxes = []
	confidences = []
	classIDs = []

	# loop over each of the layer outputs
	for output in layerOutputs:
		# loop over each of the detections
		for detection in output:
			# extract the class ID and confidence (i.e., probability)
			# of the current object detection
			scores = detection[5:]
			classID = np.argmax(scores)
			confidence = scores[classID]
			# filter out weak predictions by ensuring the detected
			# probability is greater than the minimum probability
			if confidence > args["confidence"]:
				# scale the bounding box coordinates back relative to
				# the size of the image, keeping in mind that YOLO
				# actually returns the center (x, y)-coordinates of
				# the bounding box followed by the boxes' width and
				# height
				box = detection[0:4] * np.array([W, H, W, H])
				(centerX, centerY, width, height) = box.astype("int")
				# use the center (x, y)-coordinates to derive the top
				# and and left corner of the bounding box
				x = int(centerX - (width / 2))
				y = int(centerY - (height / 2))
				# update our list of bounding box coordinates,
				# confidences, and class IDs
				boxes.append([x, y, int(width), int(height)])
				confidences.append(float(confidence))
				classIDs.append(classID)
	# apply non-maxima suppression to suppress weak, overlapping
	# bounding boxes
	idxs = cv2.dnn.NMSBoxes(boxes, confidences, args["confidence"],
		args["threshold"])
	# ensure at least one detection exists
	if len(idxs) > 0:
		# loop over the indexes we are keeping
		for i in idxs.flatten():
			# extract the bounding box coordinates
			(x, y) = (boxes[i][0], boxes[i][1])
			(w, h) = (boxes[i][2], boxes[i][3])
			print(LABELS[classIDs[i]], x, y, w, h, W, H)
			# draw a bounding box rectangle and label on the frame
			
			if not cards_played[LABELS[classIDs[i]]]:
				if y+h/2 > H/2: # if card is on bottom side of the screen
					player += cardToNum[LABELS[classIDs[i]][0]]
				else: # assume that dealer is on top side of screen
					dealer += cardToNum[LABELS[classIDs[i]][0]]
				cards_played[LABELS[classIDs[i]]] = 1

				if LABELS[classIDs[i]][0] in subtract:
					curr_count -= 1
				elif LABELS[classIDs[i]][0] in add:
					curr_count += 1

			color = [int(c) for c in COLORS[classIDs[i]]]
			cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
			text = "{}: {:.4f}".format(LABELS[classIDs[i]],
				confidences[i])
			cv2.putText(frame, text, (x, y - 5),
				cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

			print(player, dealer, curr_count)
			if random.random() > 0.5:
				print('hit')
			else:
				print('stand')


	# check if the video writer is None
	if writer is None:
		# initialize our video writer
		fourcc = cv2.VideoWriter_fourcc(*"MJPG")
		writer = cv2.VideoWriter(args["output"], fourcc, 30,
			(frame.shape[1], frame.shape[0]), True)
		# some information on processing single frame
		if total > 0:
			elap = (end - start)
			print("[INFO] single frame took {:.4f} seconds".format(elap))
			print("[INFO] estimated total time to finish: {:.4f}".format(
				elap * total))
	# write the output frame to disk
	cv2.imshow('Input', frame)
	if cv2.waitKey(1) & 0xFF == ord('q'):
		break

# release the file pointers
print("[INFO] cleaning up...")
# writer.release()
vs.release()

#            ch = 0xFF & cv2.waitKey(1000)