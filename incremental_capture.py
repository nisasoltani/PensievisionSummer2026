#import libraries
from struct import pack, unpack
import serial
import time
from picamera2 import Picamera2

#define global variables
picam2 = Picamera2()
closeLoopPos = 0 #unit: nm, minimum step: 10 nm
destination = 0x50 #Destination Byte. 0x50 for generic USB hardware unit. 
source = 0x01 #Source Byte
x_channel = 0x01 #define x channel
y_channel = 0x02 #define y channel

def main():
        #open serial port
        ser=serial.Serial("/dev/ttyUSB0" ,baudrate=115200,bytesize=8,
                        parity=serial.PARITY_NONE,stopbits=1,xonxoff=0,
                        rtscts=0,timeout=1)

        #flush input and output buffer
        ser.flushInput()
        ser.flushOutput()

        #test enabling both channels
        channelStatus = Enable(ser, x_channel)
        if channelStatus == 0:
                print("Failed to enable channel", x_channel)
                ser.close()
                return 1
        elif channelStatus == 1:
                print("Opened channel", x_channel, "successfully.")
        elif channelStatus == -1:
                return 1

        channelStatus = Enable(ser, y_channel)
        if channelStatus == 0:
                print("Failed to enable channel", y_channel)
                ser.close()
                return 1
        elif channelStatus == 1:
                print("Opened channel", y_channel, "successfully.")
        elif channelStatus == -1:
                return 1

        #set up camera
        config = picam2.create_still_configuration(
                main={"size": (1640, 1232)} #set resolution and bit size
        )
        picam2.configure(config)

        picam2.set_controls({
                "AeEnable": False,      #turn off auto exposure
                "AwbEnable": False,     #turn off auto white balance
                "AnalogueGain": 1.0,    #set analogue gain
                "ExposureTime": 30000   #set exposure time
        })

        picam2.start()
        time.sleep(2)
        #set the parameters for the loop
        step_size = 100000 #step size is 100microns
        max_distance = 5000000 #max distance is 5mm
        image_destination = "incremental_images/"

        #create loop
        for y in range(0, max_distance + 1, step_size):
                #enable channel
                channelStatus = Enable(ser, y_channel)
                if channelStatus == 0:
                        print("Failed to enable channel", y_channel, "at step", str(y))
                        return 1
                if channelStatus == 1:
                        print("Enabled channel", y_channel, "at step", str(y))
                if channelStatus == -1:
                        return 1
                #set operation to closed loop
                command = pack('<HBBBB',0x0640,y_channel, 0x02, destination, source)
                ser.write(command)
                time.sleep(0.05)

                #flush input and output buffer
                ser.flushInput()
                ser.flushOutput()

                #set closed loop move parameter
                command = pack('<HBBBBHHl',0x08C0, 0x08, 0x00, destination, source, 0x47, y_channel, y)
                ser.write(command)
                time.sleep(0.05)

                #flush input and output buffer
                ser.flushInput()
                ser.flushOutput()

                #closed loop move
                command = pack('<HBBBB',0x2100, y_channel, 0x01, destination, source)
                ser.write(command)
                time.sleep(0.05)

                #flush the input and output buffer
                ser.flushInput()
                ser.flushOutput()

                #enable x channel
                channelStatus = Enable(ser, y_channel)
                if channelStatus == 0:
                        print("Failed to enable channel", x_channel, "at step", str(y))
                        return 1
                if channelStatus == 1:
                        print("Enabled channel", x_channel, "at step", str(y))
                if channelStatus == -1:
                        return 1

                #set x operation to closed loop
                command = pack('<HBBBB',0x0640, x_channel, 0x02, destination, source)
                ser.write(command)
                time.sleep(0.05)

                #flush input and output buffer
                ser.flushInput()
                ser.flushOutput()

                #create imaging loop
                for x in range(0, max_distance + 1, step_size):
                        #set closed loop move parameter
                        command = pack('<HBBBBHHl',0x08C0, 0x08, 0x00, destination, source, 0x47, x_channel, x)
                        ser.write(command)
                        time.sleep(0.05)

                        #flush input and output buffer
                        ser.flushInput()
                        ser.flushOutput()

                        #closed loop move
                        command = pack('<HBBBB',0x2100, x_channel, 0x01, destination, source)
                        ser.write(command)
                        time.sleep(0.05)

                        #flush the input and output buffer
                        ser.flushInput()
                        ser.flushOutput()

                        #capture image
                        y_mm = y/1000000
                        x_mm = x/1000000
                        picam2.capture_file(image_destination +f"image_{y_mm:.1f}_{x_mm:.1f}.jpg")

        picam2.stop()
        return 1

def Enable(ser, channel):
        #enable the channel
        command = pack('<HBBBB',0x0210, channel, 0x01, destination, source)
        ser.write(command)
        time.sleep(0.05)

        #request the channel status
        command = pack('<HBBBB',0x0211, channel, 0x00, destination, source)
        ser.write(command)
        time.sleep(0.05)

        #get channel status
        channelStatus = 0
        Rx = ser.read_all()
        if len(Rx) >= 6:
                channelStatus = Rx[3]
        else:
                print("Failed to receive bytes to confirm channel status")
                return -1

        #flush input and output buffer
        ser.flushInput()
        ser.flushOutput()

        return channelStatus

main()

