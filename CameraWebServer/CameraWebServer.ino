#include "esp_camera.h"
#include <WiFi.h>

#define CAMERA_MODEL_AI_THINKER // Has PSRAM

#include "camera_pins.h"

const char* ssid = "schivu-laptop";
const char* password = "P@ssw0rd!123";

// DNS that points to the server
String serverName = "smart-park.go.ro";
String serverPath = "/upload.php";
const int serverPort = 80; // port for the camera upload request
const int sensorID = 1; // hardcoded ID of the device

const int pingPin = 12; // Trigger Pin of Ultrasonic Sensor
const int echoPin = 13; // Echo Pin of Ultrasonic Sensor
const int redLed = 15; // Red LED pin
const int greenLed = 14; // Green LED pin

void startCameraServer();
String sendPhoto();

WiFiClient client;

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  
  // if PSRAM IC present, init with UXGA resolution and higher JPEG quality
  //                      for larger pre-allocated frame buffer.
  if(psramFound()){
    config.frame_size = FRAMESIZE_UXGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }

#if defined(CAMERA_MODEL_ESP_EYE)
  pinMode(13, INPUT_PULLUP);
  pinMode(14, INPUT_PULLUP);
#endif

  // camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  sensor_t * s = esp_camera_sensor_get();
  // initial sensors are flipped vertically and colors are a bit saturated
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1); // flip it back
    s->set_brightness(s, 1); // up the brightness just a bit
    s->set_saturation(s, -2); // lower the saturation
  }
  // drop down frame size for higher initial frame rate
  s->set_framesize(s, FRAMESIZE_QVGA);

#if defined(CAMERA_MODEL_M5STACK_WIDE) || defined(CAMERA_MODEL_M5STACK_ESP32CAM)
  s->set_vflip(s, 1);
  s->set_hmirror(s, 1);
#endif

  WiFi.begin(ssid, password); // Connect to the network

  while (WiFi.status() != WL_CONNECTED) { // Wait until connection is established
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");

  startCameraServer();

  Serial.print("Camera Ready! Use 'http://");
  Serial.print(WiFi.localIP());
  Serial.println("' to connect");

  // Set all the required GPIO pin modes to output
  pinMode(pingPin, OUTPUT);
  pinMode(echoPin, INPUT);
  pinMode(redLed, OUTPUT);
  pinMode(greenLed, OUTPUT);
}

// sound travels 1cm in aproximately 29us, back and forth
long microsecondsToCentimeters(long microseconds) {
   return microseconds / 29 / 2;
}

int readSensor(){
   long duration, cm;
   
   digitalWrite(pingPin, LOW);
   delayMicroseconds(2);
   // Send a 10us long 40KHz pulse from the transmitter
   digitalWrite(pingPin, HIGH);
   delayMicroseconds(10);
   digitalWrite(pingPin, LOW);

   // send HIGH pulse to echo pin to listen for bounce back and measure the duration
   duration = pulseIn(echoPin, HIGH);

   // convert the duration to cm knowing that sound travels at 340m/s
   cm = microsecondsToCentimeters(duration);
   Serial.println("Sensor reading: " + String(cm) + "cm");

   return cm;
}

int state = 0; // initial state is empty
int second = 1000;
int minute = 60 * second;

// if a car is parked, check spot state every 5 minutes
int parkedDelay = 5 * minute;
// if no car is parked, check spot state every 10 seconds
int freeDelay = 10 * second;
// increment state check intervals to check for car changes
int intervalCount = 0;

int distance = 0;

void loop() {
  // read the distance measured by the sonar
  distance = readSensor();
  
  if (distance != 0) { // if the distance is 0, there could be a hardware issue regarding the sonar
    if(state == 0){
      // if the spot is empty, turn on the green led
      digitalWrite(greenLed, HIGH);
      
      // if an object gets closer than 100cm, trigger the occupation of the spot
      if(distance <= 100){
        Serial.println("Spot ID: " + String(sensorID) + " has been occupied. Sending capture...");

        // reset the ocupation interval count
        intervalCount = 0;
        
        // turn off the green led
        digitalWrite(greenLed, LOW);
        // turn on the red led to mark the spot as occupied
        digitalWrite(redLed, HIGH);

        // set the state to 1 (occupied)
        state = 1;
        // take a photo and send it to the server
        sendPhoto();
        // wait for 5 minutes to check the spot again
        delay(parkedDelay);
      }else{
        // the spot is still empty, so we wait for 10s to check again
        Serial.println("Spot ID: " + String(sensorID) + " is still free.");
        delay(freeDelay);
      }
    }else{
      // if the spot is occupied, turn on the red led 
      digitalWrite(redLed, HIGH);
      
      // if the sonar reads more than 100cm, mark the spot as vacant
      if(distance > 100){
        Serial.println("Spot ID: " + String(sensorID) + " has been freed. Sending capture...");
        // set the occupancy status to 0
        state = 0;
        digitalWrite(greenLed, HIGH);
        digitalWrite(redLed, LOW);

        // send a photo with the empty spot
        sendPhoto();
        // start waiting for 10s
        delay(freeDelay);  
      }else{
        Serial.println("Spot ID: " + String(sensorID) + " is still occupied.");
        // if the spot has been occupied for three consecutive parking intervals (15 min)
        // check if the parked car is the same
        if(intervalCount >= 2){
          Serial.println("Checking for car change at spot ID: " + String(sensorID) + " ; Sending capture...");
          // send a photo and let the server decide if the plate of the car is the same
          sendPhoto();
          // start counting for another 3 intervals
          intervalCount = 0;
        }
        // increment the interval number
        intervalCount++;
        delay(parkedDelay); // wait 5 min until next check
      }
    }
  } else{
    // if the sonar is reading 0cm, a hardware issue may have occured
    Serial.println("Sensor is reading 0cm - check for hardware issues");
    delay(2000);
  }
}

String sendPhoto() {
  String getAll;
  String getBody;

  camera_fb_t * fb = NULL;
  // take photo
  fb = esp_camera_fb_get();
  if(!fb) {
    Serial.println("Camera capture failed");
    delay(1000);
    ESP.restart();
  }
  
  Serial.println("Connecting to server: " + serverName);

  // Establish a connection to the backend server
  if (client.connect(serverName.c_str(), serverPort)) {
    // Start building the POST request containing the camera capture
    Serial.println("Connection successful!");    
    String head = "--ESP32CAM\r\nContent-Disposition: form-data; name=\"imageFile\"; filename=\"esp32-cam.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n";
    String tail = "\r\n--ESP32CAM--\r\n";
    String postSensor = "--ESP32CAM\r\nContent-Disposition: form-data; name=\"sensorID\"\r\n\r\n" + String(sensorID) + "\r\n";
    String postState = "--ESP32CAM\r\nContent-Disposition: form-data; name=\"occupied\"\r\n\r\n" + String(state) + "\r\n";

    uint32_t imageLen = fb->len;
    uint32_t extraLen = head.length() + tail.length();
    uint32_t paramsLen = postSensor.length() + postState.length();
    uint32_t totalLen = imageLen + extraLen + paramsLen;
  
    client.println("POST " + serverPath + " HTTP/1.1");
    client.println("Host: " + serverName);
    client.println("Content-Length: " + String(totalLen));
    client.println("Content-Type: multipart/form-data; boundary=ESP32CAM");
    client.println();
    client.print(postSensor);
    client.print(postState);
    client.print(head);
  
    uint8_t *fbBuf = fb->buf;
    size_t fbLen = fb->len;
    for (size_t n=0; n<fbLen; n=n+1024) {
      if (n+1024 < fbLen) {
        client.write(fbBuf, 1024);
        fbBuf += 1024;
      }
      else if (fbLen%1024>0) {
        size_t remainder = fbLen%1024;
        client.write(fbBuf, remainder);
      }
    }   
    client.print(tail);
    
    esp_camera_fb_return(fb);
    
    int timoutTimer = 10000;
    long startTimer = millis();
    boolean state = false;
    
    while ((startTimer + timoutTimer) > millis()) {
      Serial.print(".");
      delay(100);      
      while (client.available()) {
        char c = client.read();
        if (c == '\n') {
          if (getAll.length()==0) { state=true; }
          getAll = "";
        }
        else if (c != '\r') { getAll += String(c); }
        if (state==true) { getBody += String(c); }
        startTimer = millis();
      }
      if (getBody.length()>0) { break; }
    }
    Serial.println();
    client.stop();
    Serial.println(getBody);
  }
  else {
    getBody = "Connection to " + serverName +  " failed.";
    Serial.println(getBody);
  }
  return getBody;
}
