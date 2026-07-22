#import libraries
from picamera2 import Picamera2
from libcamera import controls
import time
import numpy as np
import imageio as iio
from libcamera import controls

picam2 = Picamera2()

#specify image amount
IMAGE_COUNT = 200

#set configuration parameters for the picam
def configure_picam():
        #set configuration for maximum speed
        config = picam2.create_video_configuration( 
                buffer_count=4,
                raw={"size": (1536, 864), "format": "SRGGB10"},        #size specifies resolution, format specifies sensor mode
       )
        picam2.configure(config)

        picam2.set_controls({
                "FrameRate": 121,       #max framerate for 1536x864
                "AeEnable": False,      #turn off auto exposure
                "AwbEnable": False,     #turn off white balance
                "NoiseReductionMode": 0, #turn off noise reduction
                "Sharpness": 0,         #specify sharpness
                "Contrast": 1.0,        #specify contrast
                "Saturation": 0,        #specify saturation
                "ExposureTime": 8333,  #specify exposure time (about 8333us max for 120fps)
                "AnalogueGain": 1.0,     #specify analogue gain
                "AfMode": controls.AfModeEnum.Manual,    #specify manual focus
                "LensPosition": 10      #Focuses at 10cm
        })

        #use to check sensor modes and camera configuration
        #print(picam2.sensor_modes)     #NOTE: using this command will CHANGE specified configuration
        #print(picam2.camera_configuration())

#capture a raw array of images and return array
def capture_image_array():
        #create timer start point
        t0 = time.perf_counter()

        #capture raw images and add them to array
        frames = []
        for i in range(IMAGE_COUNT):
                frame = picam2.capture_array("raw")     #captures a basic array of the image, will convert later
                frames.append(frame)

                #to test speed without capturing image, comment out the above two lines and uncomment the below two lines
               #request = picam2.capture_request()      
               #request.release()

        #mark timer end point
        t1 = time.perf_counter()

        #measure fps
        fps = IMAGE_COUNT / (t1-t0)
        print(f"FPS: {fps:.2f}")


        return frames

def main():
        #set picam configuration
        configure_picam()

        #start the picam
        picam2.start()
        time.sleep(2)

        #capture raw images
        image_array = capture_image_array()
        np.save("raw_frame_50msst.npy", image_array)
        
        #stop the picam
        picam2.stop()

main()
