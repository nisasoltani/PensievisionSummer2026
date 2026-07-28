#import libraries
import RPi.GPIO as gp
from smbus2 import SMBus
import os
from picamera2 import Picamera2
import time

#set picam2 to equal the camera 0 on Pi5, on Pi4 remove the 0
picam2 = Picamera2(0)

#create class
class MultiCameraAdapter:
        #physical header pins
        SEL0 = 7
        SEL1 = 11
        SEL2 = 12

        #camera selection table
        _CAMERAS = {
                "A": {"i2c": 0x04, "gpio": (False, False, True)},
                "B": {"i2c": 0x05, "gpio": (True, False, True)},
                "C": {"i2c": 0x06, "gpio": (False, True, False)},
                "D": {"i2c": 0x07, "gpio": (True, True, False)}
        }

        #initialize class
        def __init__(self, i2c_bus=1, mux_addr=0x70):
                #define i2c and gpio settings
                self.bus = SMBus(i2c_bus)
                self.mux_addr = mux_addr

                gp.setwarnings(False)
                gp.setmode(gp.BOARD)

                #configure pins as outputs
                gp.setup(self.SEL0, gp.OUT)
                gp.setup(self.SEL1, gp.OUT)
                gp.setup(self.SEL2, gp.OUT)

                #set the current camera to none
                self.current_camera = None

        #turn a particular camera on
        def select(self, camera):
                camera = camera.upper()

                if camera not in self._CAMERAS:
                        raise ValueError(f"Unknown camera '{camera}'")

                cfg = self._CAMERAS[camera]

                #set GPIO selection
                gp.output(self.SEL0, cfg["gpio"][0])
                gp.output(self.SEL1, cfg["gpio"][1])
                gp.output(self.SEL2, cfg["gpio"][2])

                #set i2c
                self.bus.write_byte_data(self.mux_addr, 0x00, cfg["i2c"])

                self.current_camera = camera
       #get current camera
        def current(self):
                return self.current_camera

        #close the i2c bus, camera and gpio
        def close(self):
                self.bus.close()
                gp.cleanup()
                picam2.stop()

        #make sure there's a clean switch between cameras
        def switch_camera(self, camera, settle_time=0.5):
                try:
                        picam2.stop()
                except RuntimeError:
                        pass

                self.select(camera)
                time.sleep(settle_time)
                config = picam2.create_still_configuration()
                picam2.configure(config)
                picam2.start()

        #take images with every camera
        def TakeAllImages(self, destination=""):
                self.switch_camera("A")
                picam2.capture_file(destination + "capture_A.jpg")
                self.switch_camera("B")
                picam2.capture_file(destination + "capture_B.jpg")
                self.switch_camera("C")
                picam2.capture_file(destination + "capture_C.jpg")
                self.switch_camera("D")
                picam2.capture_file(destination + "capture_D.jpg")

mux = MultiCameraAdapter()
