import cv2
from ultralytics import YOLO
import torch
import serial
import time
import os
import psutil
import numpy as np

# Variables
isIdle = False 
## Text Variables
FONT_SIZE = .5
TEXT_COLOR = (255,255,255)
THICKNESS = 1 

alpha = .2 # Transparent value
last_cell_detected = 0 # Last cell the weed was detected in 
time_detected = 0 # Total amount of times weeds were detected in session
value = 27 # Trained Model 


last_trigger = [0,0]
cooldown = 1.5


class Grid:
    def __init__(self,cell_name,x1_axis,x2_axis,y1_axis,y2_axis):
        self.cell_name = cell_name
        self.x1_axis = x1_axis
        self.x2_axis = x2_axis
        self.y1_axis = y1_axis
        self.y2_axis = y2_axis

def send_signal():
    print(f"Sending high signal now..")


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

def save_to_file(x1,y1, name):
    with open("test.txt", "a") as info:
        info.write(f"Cell: {name} | X: {x1}, Y:{y1} \n")


def arduinoSignal(ser, a):  
    ser.write(a.encode('utf-8')) 
    print(f"Sent: {a.strip()}")


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


def idle():
    global isIdle

    name = "AGRIS START"
    cv2.namedWindow(name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    background_idle = np.zeros((480,640,3), dtype =np.uint8)

    cv2.putText(background_idle, "A G R I S", (247, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
    cv2.putText(background_idle, "Press to Start", (210,280), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

    def mouse_callback(event, x, y, flags, param):
        global isIdle
        if event == cv2.EVENT_LBUTTONDOWN:
            isIdle = True

    cv2.setMouseCallback(name, mouse_callback)    

    while not isIdle:
        cv2.imshow(name, background_idle)


        k= cv2.waitKey(1) & 0xFF
        if k == ord('q'): # press q to quit 
            break
 
    cv2.destroyAllWindows()
def weed_detection():

    #Global Variables
    global last_cell_detected, time_detected

   
    face_model = YOLO(f"runs/detect/train{value}/weights/best.pt")

    cv2.namedWindow("AGRIS", cv2.WINDOW_NORMAL)

    cv2.setWindowProperty("AGRIS", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    face_camera = cv2.VideoCapture(0)

# Talks to the teensy 4.1 
   # try:
    #    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    #    time.sleep(2)
   # except serial.SerialException as e:
   #     print(f"There was an error opening serial port: {e} ")
        #exit()

    #FPS

    tick = cv2.getTickCount()
    freq = cv2.getTickFrequency()

    while face_camera.isOpened():
        verify, frame = face_camera.read()
        if not verify:
            break
        # Replace with variables for ease-of-use
        cpu_temp = get_cpu_temp()
        cpu_usage = get_cpu_usage()
        current_tick = cv2.getTickCount()

        time_fps = (current_tick - tick) / freq
        fps = 1.0 / time_fps
        tick = current_tick
        normalized_fps = .2 * fps + (1 - .2) * fps
        cell_01 = Grid("cell-01", 0, 319, 300, 480)
        cell_02 = Grid("cell-02", 322, 639, 300, 480)
        #cell_03 = Grid("cell-03", 321, 480, 300, 480)
        #cell_04 = Grid("cell-04", 481, 640, 300, 480)
        overlay = frame.copy()

        small_frame = cv2.resize(frame, (320, 320))
        current_results = face_model(small_frame, conf=0.5, verbose=False)
        #current_results = face_model(frame, conf=.50, verbose = False)
        cv2.rectangle(frame, (445,0), (640,110), (100, 100, 100), -1)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


       
        cv2.putText(frame, f"CPU-Usage: {cpu_usage}", ((450), (20)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, TEXT_COLOR,THICKNESS)
        cv2.putText(frame, f"CPU-Temp: {cpu_temp}", ((450), (40)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, TEXT_COLOR,THICKNESS)
        cv2.putText(frame, f"Weed Detected: {last_cell_detected}", ((450), (60)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, TEXT_COLOR,THICKNESS)
        cv2.putText(frame, f"Total Detections: {time_detected}", ((450), (80)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, TEXT_COLOR,THICKNESS)
        cv2.putText(frame, f"FPS: {int(normalized_fps)}", ((450), (100)), cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, TEXT_COLOR,THICKNESS)

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
        scale_x = frame.shape[1] / 320
        scale_y = frame.shape[0] / 320
        # This will take each invidiual frame that has been predicted with face_model and draw bounding boxes around them 
        current_time = time.time()
        for result in current_results:
            boxes = result.boxes
            for box in boxes:
               
                #x1, y1, x2, y2 = map(int, box.xyxy[0]) # Takes the cooridnates out of a tensor and then changes the value from float to int for cv2

                x1, y1, x2, y2 = box.xyxy[0]

                # Scale back to original frame size
                x1 = int(x1 * scale_x)
                x2 = int(x2 * scale_x)
                y1 = int(y1 * scale_y)
                y2 = int(y2 * scale_y)
                confidence = box.conf[0].item() # confidence for the identified class
                
                bounding_x = (x1 + x2) / 2
                bounding_y = (y1 + y2) / 2
                grid = [(cell_01, "Cell-01", '0'), (cell_02, "Cell-02", '1')]
                for i, (cell, label, signal) in enumerate(grid):
                    grid_system = (
                        bounding_y > cell.y1_axis and cell.x1_axis < bounding_x < cell.x2_axis
                    )
                    if grid_system:
                        if current_time - last_trigger[i] > cooldown:
                            last_trigger[i] = current_time
                            last_cell_detected = label
                            time_detected += 1
                            
                            save_to_file(x1,y1, label)
                            #arduinoSignal(ser, signal)
                            print(f"Weed detected at {label}, moving AFS 5 feet forward..., and signal {signal}")
                     

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
    cv2.destroyAllWindows()

def main():
    idle()
    weed_detection()




if __name__ == "__main__":
    main()


