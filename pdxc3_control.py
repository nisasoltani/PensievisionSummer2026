import libraries
from struct import pack, unpack
import serial
import time
from picamera2 import Picamera2

#define global variables
picam2 = Picamera2()
destination = 0x50
source = 0x01
port = "/dev/ttyUSB0"

#create class
class PDXC3Stage:
        def __init__(self):
                self.ser = serial.Serial(port, baudrate=115200, bytesize=8,
                                parity=serial.PARITY_NONE, stopbits=1,
                                xonxoff=0, rtscts=0, timeout=1)

                self.position = {1: 0, 2:0}

        def enable(self, channel):
                #enable the channel
                command = pack('<HBBBB',0x0210, channel, 0x01, destination, source)
                self.ser.write(command)
                time.sleep(0.05)

                #request the channel status
                command = pack('<HBBBB',0x0211, channel, 0x00, destination, source)
                self.ser.write(command)
                time.sleep(0.05)

                #get channel status
                channelStatus = 0
                Rx = self.ser.read_all()
                if len(Rx) >= 6:
                        channelStatus = Rx[3]
                else:
                        print("Failed to receive bytes to confirm status")
                        return -1

                #flush input and output buffer
                self.ser.flushInput()
                self.ser.flushOutput()

                return channelStatus

        def set_closed_loop(self, channel):
                command = command = pack('<HBBBB', 0x0640, channel, 0x02,
                       destination, source)
                self.ser.write(command)
                time.sleep(0.05)

        def get_position(self, channel):
                #request device status
                command = pack('<HBBBB',0x08E0, 0x00, 0x00, destination, source)
                self.ser.write(command)
                time.sleep(0.5)

                Rx = self.ser.read_all()

               if len(Rx) >= 20:
                        currentPos, encCount, statusBits = unpack('<llL', Rx[8:20])
                else:
                        print("Failed to get read bytes")
                return currentPos

        def move(self, channel, position):
                position_nm = int(position*1000000)

                self.enable(channel)
                self.set_closed_loop(channel)

                #set closed loop move parameter
                command = pack('<HBBBBHHl',0x08C0, 0x08, 0x00, destination, source, 0x47, channel, position_nm)
                self.ser.write(command)
                time.sleep(0.05)

                #flush input and output buffer
                self.ser.flushInput()
                self.ser.flushOutput()

                #closed loop move
                command = pack('<HBBBB',0x2100, channel, 0x01, destination, source)
                self.ser.write(command)
                time.sleep(0.5)

                #flush input and output buffer
                self.ser.flushInput()
                self.ser.flushOutput()

                current_pos = self.get_position(channel)/1000000

                print(f"Stage is at {current_pos} mm")

        def step(self, channel, step_size):
                self.move(channel, self.get_position(channel)/1000000 + step_size)

stage = PDXC3Stage()

