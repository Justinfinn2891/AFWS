#define C1UART Serial1

#include "RPLidarC1.h"
#include "RANSAC.h"
#include "StateMachine.h"
#include "AGVPins.h"
#include "Sensors.h"
#include <Wire.h>
#include <vector>
#include <deque>
#include <LSM6.h> 

using namespace std;

RPLidarC1 lidar(&Serial1);
RPLidarHealth health;

RPLidarMeasurement m;
RANSAC ransacRight;
RANSAC ransacLeft;

sensors processIMU;

LSM6 imu;

StateMachine S;

unsigned long startTime = 0;
bool active[4] = {false, false, false, false};


//Double Ended Queues for both sides of the car that the LiDAR is reading into
//Using Deques due its ability to remove form the from and back, which is needed for our rolling buffer 
deque<float> leftSideAngles, leftSideDistances;
deque<float> rightSideAngles, rightSideDistances;

//Thresh-hold for how far a wall should be before there needs to be gradual course correction 
float xsoftThreshhold = 127; //Reads in mm, 127mm = 5in

//Consant distances for when only on wall is applicable in mm
const float desiredOneLineDistance = 203.20;

//Limits the amount in a deque to around 3-5 seconds worth of LiDAR data.
// 18000 (angle and distance) -> ~5 seconds. 
// 9000 per side, with 4500 split between angle in distance.
static size_t dequeLimit = 150;

uint8_t error, address;

void setup() {
  Serial.begin(115200);
  Serial2.begin(9600);
  delay(2000);

  pins p;
  pinMode(20, OUTPUT);
  pinMode(21, OUTPUT);
  pinMode(22, OUTPUT);
  pinMode(23, OUTPUT);

  pinMode(p.PWM1, OUTPUT);
  pinMode(p.PWM2, OUTPUT);
  pinMode(p.INA1, OUTPUT);
  pinMode(p.INA2, OUTPUT);
  pinMode(p.INB1, OUTPUT);
  pinMode(p.INB2, OUTPUT);
  pinMode(p.INB1, OUTPUT);
  pinMode(p.INB2, OUTPUT);

  Serial.println("Initializing RPLidar...");
  if (!lidar.begin(460800, 4000)) {
    Serial.println("Failed to initialize RPLidar.");
    while (1) delay(1000);
  }

  if(lidar.get_health(&health)) {
    lidar.print_health(&health);
    if(health.status != RPLIDAR_STATUS_OK) {
      Serial.println("Warning: LiDAR not healthy, attempting reset...");
      lidar.reset();
      delay(2000);
    }
  }
  else
    Serial.println("Failed to get health status.");

  if(!lidar.start_scan()){
    Serial.println("Failed to start scan");
    while(1) delay(1000);
  }
  Serial.println("Scan started successfully");

  Wire.begin();

  Wire.setClock(400000);

  imu.enableDefault();

  long sum = 0;
  int samples = 500;
  for(int i = 0; i < samples; i++){
    imu.read();
    sum += imu.g.z;
    delay(2);
  }

  processIMU.biasZ = (float)sum/samples;
  Serial.println("Bias found: ");
  Serial.print(processIMU.biasZ);

  S.STATE = S.STOP;
}

void clearSerialBuffer() {
  while (Serial.available()) Serial.read();
}

void triggerCell(int cell) {
  digitalWrite(cell + 13, HIGH);   // activate
  startTime = millis();
  active[cell] = true;
}


void loop() {
  // Vectors to hold the converted LiDAR points
 // Read newest serial command
  if (Serial.available()) {
    char c = Serial.read();
    clearSerialBuffer();

    if (c >= '0' && c <= '3') {
      int cell = c - '0';
      triggerCell(cell);
      Serial.println(cell);
    }
  }

  // Non-blocking timer control
  for (int i = 0; i < 4; i++) {
    if (active[i] && millis() - startTime > 3000) {
      digitalWrite(i + 13, LOW);   // deactivate
      active[i] = false;
    }
  }
  static float lineDifference = 0.0f;
  static float rightDistance = 0.0f;
  static float leftDistance = 0.0f;


  static float rightOnlyDistanceDifference = 0.0f;
  static float leftOnlyDistanceDifference = 0.0f;


  //Timers for stop, searching_for_walls, and end_of_row states
  static unsigned long stopStartTime = 0;
  static unsigned long timeSinceValidation = 0;
  static unsigned long timeSinceSearchShift = 0;

  imu.read();

  static vector<points> rightCartesianConverted;
  static vector<points> leftCartesianConverted;

  float rawZ = imu.g.z;
  float centeredZ = rawZ - processIMU.biasZ;

  processIMU.filteredGyroZ = (processIMU.filteredGyroZ *(1.0 - processIMU.alpha)) + (centeredZ * processIMU.alpha);

  float zRateDegressPerSecond = processIMU.filteredGyroZ * 0.070f;

  if (lidar.get_measurement(&m)) {

  //Checks if detect angles are within a certain thresh-hold.
  //45 -> 135 degrees is right side
  //225 -> 315 is left side.
    if (m.angle > 45 && m.angle <= 135) {
      rightSideAngles.push_back(m.angle);
      rightSideDistances.push_back(m.distance);
    } 
    else if (m.angle > 225 && m.angle <= 315) {
      leftSideAngles.push_back(m.angle);
      leftSideDistances.push_back(m.distance);
    }

  //If the size of one of the angle deques is greater than the dequeLimit (4500)...
  //Start a rolling buffer that will delete the beginning of the deque and add another data point.
    while (rightSideAngles.size() > dequeLimit) {
      rightSideAngles.pop_front();
        if (!rightSideDistances.empty()){
          rightSideDistances.pop_front();
        } 
    }

    while (leftSideAngles.size() > dequeLimit) {
      leftSideAngles.pop_front();
      if (!leftSideDistances.empty()){
        leftSideDistances.pop_front();
      } 
    }


  // This will only start the RANSAC and STATEMACHINE process whennever a rotation starts 
    if (m.start_flag) {
    // Wait until there is at-least 50 data points for both sides
      if (leftSideAngles.size() > 50 || rightSideAngles.size() > 50) {
    // Clear vectors
        leftCartesianConverted.clear();
        rightCartesianConverted.clear();

    // Convert r and thada to x and y for RANSAC
        ransacRight.cartesianConversion(rightSideAngles, rightSideDistances, rightCartesianConverted);
        ransacLeft.cartesianConversion(leftSideAngles, leftSideDistances, leftCartesianConverted);

    // Try to find best-fit line through RANSACLoop
        ransacLeft.RANSACLoop(leftCartesianConverted);
        ransacRight.RANSACLoop(rightCartesianConverted);

    // Calculate distance from origin (the car) to the RANSAC lines
        ransacRight.distancetoLine();
        rightDistance = ransacRight.distance;

        ransacLeft.distancetoLine();
        leftDistance = ransacLeft.distance;

      // Calculation for finding the distance between RANSAC lines. Use this for PID as an error to correct.
        lineDifference = rightDistance - leftDistance;
      }
    }
  }

  static unsigned long lastMotorUpdate = 0;
  if (millis() - lastMotorUpdate >= 10) { // Run at 100Hz
    lastMotorUpdate = millis();

    switch(S.STATE) {
      //Stop, wait for 5 seconds, check line validation. If valid, switch to inbetween_rows.
      case S.STOP:
        S.stop(); 
        if (stopStartTime == 0){
          stopStartTime = millis();     
        } 

        if (millis() - stopStartTime > 5000) {
          if (ransacRight.lineValidation() || ransacLeft.lineValidation()) {
            S.STATE = S.INBETWEEN_ROWS;
            Serial.println("WALL FOUND: SWITCHING");
          }
        }
      break;

      case S.INBETWEEN_ROWS:
        // Use the difference between walls to steer via PID (inside the state machine)
        S.inbetween_rows(lineDifference, zRateDegressPerSecond);

        if(ransacRight.lineValidation() == 0 || ransacLeft.lineValidation() == 0){
          if(timeSinceValidation == 0) {
            timeSinceValidation = millis();
          }
    
          if(timeSinceValidation > 1500){
            S.STATE = S.SEARCHING_FOR_WALLS;
            timeSinceSearchShift = timeSinceValidation;
            timeSinceValidation = 0;
          }
      //If right wall is found and not left, maintain a set distance from the right wall. 
        if(ransacRight.lineValidation () == 1 && ransacLeft.lineValidation() == 0){
          if(rightDistance != 203.20){
          rightOnlyDistanceDifference = desiredOneLineDistance - rightDistance;
            S.inbetween_rows(rightOnlyDistanceDifference, zRateDegressPerSecond);
          }
        }
        else if(ransacRight.lineValidation () == 0 && ransacLeft.lineValidation() == 1){
          if(leftDistance != 203.20){
            leftOnlyDistanceDifference = desiredOneLineDistance - leftDistance;
            S.inbetween_rows(leftOnlyDistanceDifference, zRateDegressPerSecond);
          }
        }

        break;
    // If a wall hasn't been found for 1.5 seconds, slow down the vehicle. 
      case S.SEARCHING_FOR_WALLS:
        S.searching_for_walls();
        
        Serial.println("Searching...");

        //timeSinceSearchShift = timeSinceSearchShift + millis();

      if(ransacRight.lineValidation() == 1 || ransacLeft.lineValidation() == 1 ){
          S.STATE = S.INBETWEEN_ROWS;
          Serial.println("Switching back to inbetween");
      }

      //if a valid line hasn't been found for 4 seconds (plus the 1.5 from inbetween rows, so 5.5), then a row has been left.
        //if(timeSinceValidation > 4000){
          //S.STATE = S.END_OF_ROW;
        //}
      break;

      /*case S.END_OF_ROW:
        break;*/


      /*case S.DETECTED_WEED:

        break;*/
      }
    }
  }
}









