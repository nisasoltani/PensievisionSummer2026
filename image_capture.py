import smbus
from PyQt5.QtCore import QObject, pyqtSignal
from logger import logger
from picamera2 import Picamera2
from libcamera import Transform, controls
import numpy as np
import time

class LiquidLensDriver(QObject):
    disconnect = pyqtSignal()
    def __init__(self, *args, **kwargs):
        super(LiquidLensDriver, self).__init__()
        self.middlevoltage = 45.

    def loadDriver(self):
        try:
            self.driver = smbus.SMBus(1)
            self.driver.write_byte(0b0100011, 0x00)
            print("Bus ready: ", self.driver)
            return True
        except OSError as e:
            logger.error(f'LIQUID LENS NOT DETECTED: {e}')

            print(f'LIQUID LENS NOT DETECTED: {e}')
            return False

    def d_write(self, voltage=False, close=False):
        try:
            if close:
                self.driver.write_byte(0b0100011, 0x00)  # Shutdown code
                return

            if voltage:
                #print(f'writing voltage {voltage}')
                self.driver.write_byte(0b0100011, int(round(4.8846 * voltage - 47.846)) % 256)
            else:
                self.driver.write_byte(0b0100011, int(round(4.8846 * self.middlevoltage - 47.846)) % 256)
                #print(f'writing voltage {voltage}')

        except OSError as e:
            logger.error(f'LIQUID LENS DISCONNECTED: {e}')

            print(f'LIQUID LENS DISCONNECTED: {e}')
            self.disconnect.emit()
            
    def set_voltage(self, volt=False, shutdown=False):
        self.d_write(voltage=volt, close=shutdown)

lens = LiquidLensDriver()
lens.loadDriver()

picam2 = Picamera2()

#use to check sensor modes available to the camera
#print(picam2.sensor_modes)

#jpg configuration
#config = picam2.create_still_configuration(transform=Transform(vflip=True, hflip=True))

#raw image configuration
config = picam2.create_video_configuration(
       buffer_count=4,
       raw={"size": (1536, 864), "format": "SBGGR10"} #change size based on sensor modes available to camera
)
picam2.configure(config)

#set controls 
picam2.set_controls({
        "FrameRate": 121,       #set frame rate for camera
        "AeEnable": False,      #turn off auto exposure
        "AwbEnable": False,     #turn off auto white balance
        "NoiseReductionMode": 0,#set noise reduction
        "Sharpness": 0,         #set sharpness
        "Contrast": 0,          #set contrast
        "Saturation": 0,        #set saturation
        "ExposureTime": 8333,   #set exposure time (8333 for PiCamv3 120FPS, 12000 for PiCamv2 80FPS)
        "AnalogueGain": 1.0,    #set analogue gain
        #use for Pi Camera v3
       "AfMode": controls.AfModeEnum.Manual,    #turn off autofocus
       "LensPosition": 10       #set lens position (10 focuses at 10cm)
})

#start picam and give time for controls to settle
picam2.start()
time.sleep(2)

#location and name beginning for jpeg images
name_beginning = "3d_image_test/image_"

#create array for storing images
frames = []

#take start time reference
t0 = time.perf_counter()

#image counter for FPS calculation
image_counter = 0

for j in np.arange(20, 60.2, 0.2):
        lens.d_write(voltage=j)
        time.sleep(0.05)    #comment this line for fast capture
        #capture jpg images
        #picam2.capture_file(name_beginning + f"{j:.1f}" + "V.jpg")

        #capture raw images
        frame = picam2.capture_array("raw")
        frames.append(frame)

        image_counter += 1
#check fps
t1 = time.perf_counter()
fps = image_counter / (t1 - t0)
print(f"FPS: {fps:.2f}")

#save raw image array
np.save("ll_3d_picam2.npy", frames)

picam2.stop()
