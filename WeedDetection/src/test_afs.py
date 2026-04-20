import cv2
from ultralytics import YOLO
import torch
import serial
import time
import os
import psutil

# TO DO LIST
# 1.) Allow multiple "solonoids" to go off at a time 
# 3.) Automate the camera config. ie Extra camera size and divide by total cell count, apply to grid objects. 

def send_signal():
    print(f"Sending high signal now..")

def pi_camera_active():

   
    data = cv2.VideoCapture(0)
    model = YOLO("runs/detect/train21/weights/best.pt")
    while data.isOpened:
        verify, frame = data.read() #verify to call later to validity, frame for 1 frame per 4.5ms
        if not verify:
            break # breaks out of script if it can't call back a frame 
        #print(f"Video capture has been opened successfully")
        current_results = model(frame, conf =.25) #used to predict with our trained model 
        single_frame = current_results[0].plot() #plots the data in the terminal 

        cv2.imshow("yolo", single_frame) #Displays the single image in the window 
        k= cv2.waitKey(1) & 0xFF
        if k == ord('q'): # press q to quit 
            break
    
    data.release()
    data.destroyAllWindows()

def get_cpu_usage():
    return f"{psutil.cpu_percent(interval=None)}%"

def get_cpu_temp():
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return "N/A"

        for name, entries in temps.items():
            for entry in entries:
                return f"{entry.current:.1f}C"
    except:
        pass

    return "N/A"

def test():
    img = "img.jpg"
    model = YOLO("runs/detect/train21/weights/best.pt") #loads in our new model for yolov8
    weed_results = model.predict(f"../test/{img}")
    result_example = weed_results[0]
    weed_results[0].show()
    print(f"The amount of bounding boxes in this picture: {len(result_example.boxes)}")
    # Run pi camera and get results per image 
    # Get coordinates of bounding box, move target to location and spray 

# This will be used to test the face 

def save_to_file(x1,y1, name):
    with open("test.txt", "a") as info:
        info.write(f"Cell: {name} | X: {x1}, Y:{y1} \n")


def arduinoSignal(ser, a):  
    ser.write(a.encode('utf-8')) 
    print(f"Sent: {a.strip()}")

# Going to use this class to separate the frame into cells 
class Grid:
    def __init__(self,cell_name,x1_axis,x2_axis,y1_axis,y2_axis):
        self.cell_name = cell_name
        self.x1_axis = x1_axis
        self.x2_axis = x2_axis
        self.y1_axis = y1_axis
        self.y2_axis = y2_axis

# Testing code to draw out the cells before implementing it
def test_grid():
    face_camera = cv2.VideoCapture(0)
    cell_01 = Grid("cell-01", 0, 160, 300, 480)
    cell_02 = Grid("cell-02", 161, 320, 300, 480)
    cell_03 = Grid("cell-03", 321, 480, 300, 480)
    cell_04 = Grid("cell-04", 481, 640, 300, 480)
    FONT_SIZE = .5
    TEXT_COLOR = (255,255,255)
    THICKNESS = 1
    while face_camera.isOpened():
        cpu_temp = get_cpu_temp()
        cpu_usage = get_cpu_usage()

        stats = [
            f"CPU Usage: {get_cpu_usage()}",
            f"CPU Temp: {get_cpu_temp()}"
        ]

    
        verify, frame = face_camera.read()

        cv2.rectangle(frame,(cell_01.x1_axis,cell_01.y1_axis),(cell_01.x2_axis,cell_01.y2_axis),(0,255,0),3)
        cv2.rectangle(frame,(cell_02.x1_axis,cell_02.y1_axis),(cell_02.x2_axis,cell_02.y2_axis),(255,255,0),3)
        cv2.rectangle(frame,(cell_03.x1_axis,cell_03.y1_axis),(cell_03.x2_axis,cell_03.y2_axis),(0,255,255),3)
        cv2.rectangle(frame,(cell_04.x1_axis,cell_04.y1_axis),(cell_04.x2_axis,cell_04.y2_axis),(100,44,320),3)

        cv2.putText(frame, "cell-1", ((cell_01.x2_axis - 55), (cell_01.y1_axis + 20)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, TEXT_COLOR,THICKNESS)
        cv2.putText(frame, "cell-2", ((cell_02.x2_axis - 55), (cell_02.y1_axis + 20)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, TEXT_COLOR,THICKNESS)
        cv2.putText(frame, "cell-3", ((cell_03.x2_axis - 55), (cell_03.y1_axis + 20)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, TEXT_COLOR,THICKNESS)
        cv2.putText(frame, "cell-4", ((cell_04.x2_axis - 55), (cell_04.y1_axis + 20)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, TEXT_COLOR,THICKNESS)
        if not verify:
            break
        k= cv2.waitKey(1) & 0xFF
        if k == ord('q'): # press q to quit 
            break
        cv2.imshow("yolo", frame)
    face_camera.release()
    face_camera.destroyAllWindows()       

def test_face(isDetected):


    #TO DO:

    # CAPTURE THIS DATA AND STORE IN CSV
    ## Get the normal values as well 

    # ANNOTATE A FACE AND TRAIN IT WITH train.afs.py 
    # TEST THE FACE AND RUN AN ARDUINO SCRIPT TO LIGHT UP LED

    value = 27
    select = input("Would you like to use pretrained or custom trained model? 1 - Pretrain | 2 - Custom")
    
    if int(select) == 2:
        face_model = YOLO(f"runs/detect/train{value}/weights/best.pt")
    else:
        face_model = YOLO("yolov8n.pt") #Original class, we don't have the faces yet 
    cv2.namedWindow("AGRIS", cv2.WINDOW_NORMAL)

    cv2.setWindowProperty("AGRIS", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    face_camera = cv2.VideoCapture(0)

   # try:
    #    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    #    time.sleep(2)
   # except serial.SerialException as e:
   #     print(f"There was an error opening serial port: {e} ")
        #exit()
    last = 0
    time = 0
    hand_detected = [False, False, False, False]

    while face_camera.isOpened():
        verify, frame = face_camera.read()
        if not verify:
            break
        # Replace with variables for ease-of-use
        cpu_temp = get_cpu_temp()
        cpu_usage = get_cpu_usage()

        stats = [
            f"CPU Usage: {get_cpu_usage()}",
            f"CPU Temp: {get_cpu_temp()}"
        ]   
        cell_01 = Grid("cell-01", 0, 319, 300, 480)
        cell_02 = Grid("cell-02", 322, 639, 300, 480)
        #cell_03 = Grid("cell-03", 321, 480, 300, 480)
        #cell_04 = Grid("cell-04", 481, 640, 300, 480)
        overlay = frame.copy()
        current_results = face_model(frame, conf=.50, verbose = False)
        isDetected = False # save coordinates to file
        FONT_SIZE = .5
        TEXT_COLOR = (255,255,255)
        THICKNESS = 1
        alpha = .2
        cv2.rectangle(frame, (445,0), (640,100), (100, 100, 100), -1)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        cv2.putText(frame, f"CPU-Usage: {cpu_usage}", ((450), (20)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, TEXT_COLOR,THICKNESS)
        cv2.putText(frame, f"CPU-Temp: {cpu_temp}", ((450), (40)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, TEXT_COLOR,THICKNESS)
        cv2.putText(frame, f"Weed Detected: {last}", ((450), (60)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, TEXT_COLOR,THICKNESS)
        cv2.putText(frame, f"Total Detections: {time}", ((450), (80)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, TEXT_COLOR,THICKNESS)
        # Grid implementation for each individual cell
        cv2.rectangle(frame,(cell_01.x1_axis,cell_01.y1_axis),(cell_01.x2_axis,cell_01.y2_axis),(0,255,0),3)
        cv2.rectangle(frame,(cell_02.x1_axis,cell_02.y1_axis),(cell_02.x2_axis,cell_02.y2_axis),(255,255,0),3)
       # cv2.rectangle(frame,(cell_03.x1_axis,cell_03.y1_axis),(cell_03.x2_axis,cell_03.y2_axis),(0,255,255),3)
        #cv2.rectangle(frame,(cell_04.x1_axis,cell_04.y1_axis),(cell_04.x2_axis,cell_04.y2_axis),(100,44,320),3)
        # Label implementation for each individual cell 
        cv2.putText(frame, "cell-1", ((cell_01.x2_axis - 55), (cell_01.y1_axis + 20)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, TEXT_COLOR,THICKNESS)
        cv2.putText(frame, "cell-2", ((cell_02.x2_axis - 55), (cell_02.y1_axis + 20)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, TEXT_COLOR,THICKNESS)
        cv2.putText(frame, "A G R I S", ((18), (40)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE + .3, TEXT_COLOR,THICKNESS + 1)

        #cv2.putText(frame, "cell-3", ((cell_03.x2_axis - 55), (cell_03.y1_axis + 20)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, TEXT_COLOR,THICKNESS)
       # cv2.putText(frame, "cell-4", ((cell_04.x2_axis - 55), (cell_04.y1_axis + 20)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, TEXT_COLOR,THICKNESS)
   
        # This will take each invidiual frame that has been predicted with face_model and draw bounding boxes around them 
        for result in current_results:
            boxes = result.boxes
            for box in boxes:
               
                x1, y1, x2, y2 = map(int, box.xyxy[0]) # Takes the cooridnates out of a tensor and then changes the value from float to int for cv2
                confidence = box.conf[0].item() # confidence for the identified class
                
                bounding_x = (x1 + x2) / 2
                bounding_y = (y1 + y2) / 2
                #print(f"This is bounding_x: {bounding_x}, this is y: {bounding_y}")
                grid = [(cell_01, "Cell-01", '0'), (cell_02, "Cell-02", '1')]
                for i, (cell, label, signal) in enumerate(grid):
                    grid_system = (
                        bounding_y > cell.y1_axis and cell.x1_axis < bounding_x < cell.x2_axis
                    )
                    if grid_system and not hand_detected[i]:
                        last = label
                        time += 1
                        hand_detected[i] = True
                        save_to_file(x1,y1, label)
                        #arduinoSignal(ser, signal)
                        print(f"Weed detected at {label}, moving AFS 5 feet forward..., and signal {signal}")
                    elif not grid_system:
                        hand_detected[i] = False

                class_id = int(box.cls[0]) #Class id to use with the class_name 
                class_name = face_model.names[class_id]
                label = f'{class_name}, {confidence}, {x1}, {y1}' # THis is the label that is above the bounding box

                cv2.rectangle(frame, (x1,y1), (x2,y2), (0,100,0), 2) #This creates our own custom bounding box, using this instead of .plot
                cv2.putText(frame, label, (x1,y1-10), cv2.FONT_HERSHEY_SIMPLEX, .5, (0,255,0), 2) #Puts the label above the box 

        cv2.imshow("AGRIS", frame)

        k= cv2.waitKey(1) & 0xFF
        if k == ord('q'): # press q to quit 
            break
    face_camera.release()
    face_camera.destroyAllWindows()

def main():
    #pi_camera_active()
    isDetected = False
    #test_grid()
    test_face(isDetected)




if __name__ == "__main__":
    main()


