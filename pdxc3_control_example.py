from struct import pack, unpack
import serial
import time

serialPort = "COM4" #find out COM port number in the Device Manager
openLoopStep = 5 #unit: step
closeLoopPos = 0 #unit: nm, minimum step: 10 nm

#Find section "4 Description of the message header" of the APT communication protocl PDF for detail
#APT communication protocl PDF can be found https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=Motion_Control&viewtab=2
destination = 0x50 #Destination Byte. 0x50 for generic USB hardware unit. 
source = 0x01 #Source Byte
channel = 0x01 #choose the channel to control. For PDXC2, the channel is set to 0x01

def main():
    
    try:
        # open serial port
        # For Windows
        ser=serial.Serial("/dev/ttyUSB0" ,baudrate=115200,bytesize=8,
                        parity=serial.PARITY_NONE,stopbits=1,xonxoff=0,
                        rtscts=0,timeout=1)
#        for ch in [1, 2]:
#            command = pack('<HBBBB', 0x08E0, ch, 0x00, destination, source)
#            ser.write(command)
#            time.sleep(0.05)
#            rx = ser.read_all()
#            print(f"Channel {ch}: {rx.hex()}")
        # For Linux
        # use 'dmesg | grep tty' to find serial port, eventually need to change permissions for /dev/tty*
        # uncomment the following lines
        ##    ser=serial.Serial('/dev/ttyUSB0', baudrate=115200,bytesize=8,
        ##                      parity=serial.PARITY_NONE,stopbits=1,xonxoff=0,
        ##                      rtscts=0,timeout=1)  
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        return -1
    
    try:
        # Flush input and output buffer
        ser.flushInput()
        ser.flushOutput()
        # Enable the stage
        channelStatus = Enable(ser)
        if channelStatus == 0:
            print("Fail to enable the channel.")
        elif channelStatus == 1:
            print("Opened channel successfully.")
            #OpenLoopMove(ser)
            # The close loop mode is only valid for PDX series stages with encoder
            CloseLoopMove(ser)  
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ser.close()   
        print("Program finishes.")
        return 1

def Enable(ser):
    Rx = ser.read(90)
        # Request Hardware information || MGMSG_HW_REQ_INFO || 0x0005
    command = pack('<HBBBB',0x0005, 0x00, 0x00, destination, source)
    ser.write(command)
    time.sleep(0.05)
    
    # Get hardware information || MGMSG_HW_GET_INFO || 0x0006
    Rx = ser.read(90)
    if len(Rx) >= 10: 
        serialNum = unpack('<I',Rx[6:10])[0]
        print(f"Opening SN: {serialNum}")
    else:
        print("MGMSG_HW_GET_INFO: Fail to receive bytes. ")
        return -1
    
    # Flush input and output buffer
    ser.flushInput()
    ser.flushOutput()
    
    # Request device status || MGMSG_PZMOT_REQ_STATUSUPDATE ||0x08E0
    command = pack('<HBBBB',0x08E0, 0x00, 0x00, destination, source)
    ser.write(command)
    time.sleep(0.05)
    
    #Get device status of channel 1 || MGMSG_PZMOT_GET_STATUSUPDATE ||0x08E1
    Rx = ser.read(62)
    if len(Rx) >= 20:
        statusBits = unpack('<L',Rx[16:20])[0]
        # check if there are any errors in the controller's status.
        if (statusBits & 0x0F000000)!= 0:
            print(f"Status Error: 0x0{(statusBits& 0x0F000000):0x}")
            print("""Status bits:
    0x01000000 Excess current error
    0x02000000 Exces temperature error
    0x04000000 Abnormal mode detected
    0x08000000 Wrong stage detected\n""")
            return -1
    else: 
        print("MGMSG_PZMOT_GET_STATUSUPDATE: Fail to receive bytes.")
        # Flush input and output buffer
        ser.flushInput()
        ser.flushOutput() 
        return -1
    
    # Flush input and output buffer
    ser.flushInput()
    ser.flushOutput() 
    
    # enable the channel || MGMSG_MOD_SET_CHANENABLESTATE || 0x0210
    command = pack('<HBBBB',0x0210, channel, 0x01, destination, source)
    ser.write(command)
    time.sleep(0.05)
    
    # request the channel status || MGMSG_MOD_REQ_CHANENABLESTATE ||0x0211
    command = pack('<HBBBB',0x0211, channel, 0x00, destination, source)
    ser.write(command)
    time.sleep(0.05)
    
    # get the channel status || MGMSG_MOD_GET_CHANENABLESTATE ||0x0212
    channelStatus = 0
    time.sleep(0.05)
    Rx = ser.read_all()
    print("Enable response:", Rx.hex())
    if len(Rx) >= 6: 
        #channelStatus = unpack('<B',Rx[2:3])[0]
        channelStatus = Rx[3]
        print("Decoded:", Rx[:6].hex())
    else:
        print("MGMSG_MOD_GET_CHANENABLESTATE: Fail to receive bytes.")
        return -1

        # Flush input and output buffer
    ser.flushInput()
    ser.flushOutput()

    return channelStatus
    
def OpenLoopMove(ser):
    print("Open Loop Operation.")
    # Set the operating loop mode to open loop || MGMSG_PZ_SET_POSCONTROLMODE  ||0x0640
    command = pack('<HBBBB',0x0640, channel, 0x01, destination, source)
    ser.write(command)
    time.sleep(0.05)
    
    # Set the open loop move step size || MGMSG_PZMOT_SET_PARAMS (Set_PZMOT_OpenMoveParams) ||0x08C0 (sub-message ID 0x46)
    command = pack('<HBBBBHHl',0x08C0, 0x08, 0x00, destination, source, 0x46, channel, openLoopStep)
    ser.write(command)
    time.sleep(0.05)
    
    # Flush input and output buffer
    ser.flushInput()
    ser.flushOutput() 
    
    # Start Open Loop Move || MGMSG_PZMOT_MOVE_START ||0x2100
    command = pack('<HBBBB',0x2100, channel, 0x01, destination, source)
    ser.write(command)
    time.sleep(0.05)
    # Upon completion of the movement, a message will send || MGMSG_PZMOT_MOVE_COMPLETED || 0x08D6
    
    # Request device status || MGMSG_PZMOT_REQ_STATUSUPDATE ||0x08E0
    command = pack('<HBBBB',0x08E0, 0x00, 0x00, destination, source)
    ser.write(command)
    time.sleep(0.05)
    
    #Get device status and position of channel 1 || MGMSG_PZMOT_GET_STATUSUPDATE ||0x08E1
    Rx = ser.read_all()
    if len(Rx) >= 20:
        currentPos, encCount ,statusBits = unpack('<llL',Rx[8:20])
        # wait for the movement to stop
        # if Rx contains '\d6\08', it's the auto message MGMSG_PZMOT_MOVE_COMPLETED, skip and request the status again
        while ((statusBits & 0xF0) != 0) or ((b'\xd6\x08') in Rx) or Rx[0] != 0xE1:
            # Flush input and output buffer
            ser.flushInput()
            ser.flushOutput() 
            command = pack('<HBBBB',0x08E0, 0x00, 0x00, destination, source)
            ser.write(command)
            time.sleep(0.05)
            Rx = ser.read_all()
            currentPos, encCount ,statusBits = unpack('<llL',Rx[8:20])
        print(f"The stage stops at {currentPos} steps.")
        # Flush input and output buffer
        ser.flushInput()
        ser.flushOutput() 
        return 1
    else: 
        print("MGMSG_PZMOT_GET_STATUSUPDATE: Fail to receive bytes.")
        # Flush input and output buffer
        ser.flushInput()
        ser.flushOutput() 
        return -1

    
def CloseLoopMove(ser):
    print("Close Loop Operation.")
    # Set the operating loop mode to close loop || MGMSG_PZ_SET_POSCONTROLMODE ||0x0640
    command = pack('<HBBBB',0x0640, channel, 0x02, destination, source)
    ser.write(command)
    time.sleep(0.05)
    
    # Flush input and output buffer
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    time.sleep(0.1)
#    ser.flushInput()
#    ser.flushOutput()
    
    # Request device status || MGMSG_PZMOT_REQ_STATUSUPDATE ||0x08E0
    command = pack('<HBBBB',0x08E0, 0x00, 0x00, destination, source)
    ser.write(command)
    time.sleep(0.05)
    
    #Get device status of channel 1 || MGMSG_PZMOT_GET_STATUSUPDATE || 0x08E1
    Rx = ser.read(62)
#    print("Raw status packet:", Rx.hex())

 #   for i in range(0, len(Rx)-3, 4):
 #       value = unpack("<L", Rx[i:i+4])[0]
 #       print(f"{i:2d}: {Rx[i:i+4].hex()}   0x{value:08X}")

    if len(Rx) >= 20:
        statusBits = unpack('<L',Rx[16:20])[0]
#        print(f"Using statusBits = 0x{statusBits:08X}")
#        print(f"Homed bit set: {bool(statusBits & 0x0400)}")
#        print(f"Homing bit set: {bool(statusBits & 0x0200)}")
#        print(f"Moving bits: 0x{statusBits & 0x00F0:02X}")

        # check if the stage is set to close loop mode
        if (statusBits & 0x800)!= 0x800:
            print("Fail to set the mode to close loop mode.")
            return -1
    else: 
        print("MGMSG_PZMOT_GET_STATUSUPDATE: Fail to receive bytes.")
        ser.flushInput()
        ser.flushOutput() 
        return -1
    
    # Flush input and output buffer
    ser.flushInput()
    ser.flushOutput()

    command = pack('<HBBBB', 0x08E0, 0x00, 0x00, destination, source)
    ser.write(command)
    time.sleep(0.05)
    Rx = ser.read(62)
    statusBits = unpack('<L', Rx[16:20])[0]
 #   print(f"Status immediately before HOME = 0x{statusBits:08X}")

    startTime = time.time()

    if(statusBits & 0x0400):
        print("Stage already homed, skipping home.")
    else:

    # home the stage || MGMSG_MOT_MOVE_HOME ||0x0443
        command = pack('<HBBBB',0x0443, channel, 0x00, destination, source)
        ser.write(command)
        time.sleep(0.05)
    
    # Upon completion of home sequence, a message will send || MGMSG_MOT_MOVE_HOMED || 0x0444
#        startTime = time.time()
        Rx = bytearray()
#    while len(Rx) < 6:
#        new_data = ser.read(ser.inWaiting() or 1)
#        Rx.extend(new_data)
        while True:
#        Rx = ser.read(6)

#        if len(Rx) == 6:
#            print("HOME RX:", Rx.hex())
#            if Rx[0:2] == b'\x44\x04':
#                print("The stage is Homed")
#                break

            if ser.in_waiting:
                new_data = ser.read(ser.in_waiting)
                Rx.extend(new_data)
#                print("HOME waiting RX:", Rx.hex())

                if b'\x44\x04' in Rx:
                    break

            time.sleep(0.01)
            endTime = time.time()
        # overtime break
            if endTime - startTime > 30:
                print(f"Fail to home the stage")
                return -1

        print("The stage is Homed.")

    # Flush input and output buffer
#    ser.flushInput()
#    ser.flushOutput() 
        time.sleep(0.5)

        while True:
            ser.reset_input_buffer()
            command = pack('<HBBBB',0x08E0,0x00,0x00,destination,source)
            ser.write(command)
            time.sleep(0.1)

            if len(Rx) >= 20:
                statusBits = unpack('<L', Rx[16:20])[0]
#                print(f"Post-home status = 0x{statusBits:08X}")
                if (statusBits & 0x200) == 0:
                    print("Controller exited homing state.")
                    break
            if time.time() - startTime > 10:
                print("Timed out waiting for homing state to clear")
                return -1
        time.sleep(0.5)
#Set Close Loop Move Parameter|| MGMSG_PZMOT_SET_PARAMS (Set_PZMOT_CloseMovePar>
    command = pack('<HBBBBHHl',0x08C0, 0x08, 0x00, destination, source, 0x47, channel, closeLoopPos)
    ser.write(command)
    time.sleep(0.05)

    # Flush input and output buffer
    ser.flushInput()
    ser.flushOutput() 

    #Start Close Loop Move || MGMSG_PZMOT_MOVE_START ||0x2100
    command = pack('<HBBBB',0x2100, channel, 0x01, destination, source)
    ser.write(command)
    time.sleep(0.05)
    # Upon completion of the movement, a message will send || MGMSG_PZMOT_MOVE_COMPLETED || 0x08D6
    
    # Request device status || MGMSG_PZMOT_REQ_STATUSUPDATE ||0x08E0
    command = pack('<HBBBB',0x08E0, 0x00, 0x00, destination, source)
    ser.write(command)
    time.sleep(0.5)
    
    #Get device status and position of channel 1 || MGMSG_PZMOT_GET_STATUSUPDATE ||0x08E1
    Rx = ser.read(48)
    if len(Rx) >= 20:
        currentPos, encCount ,statusBits = unpack('<llL',Rx[8:20])
        # wait for the movement to stop
        # if Rx contains '\d6\08', it's the auto message MGMSG_PZMOT_MOVE_COMPLETED, skip and request the status again
#        while ((statusBits & 0xF0) != 0) or ((b'\xd6\x08') in Rx) or Rx[0] != 0xE1:
            # Flush input and output buffer
        while True:

#            ser.flushInput()
#            ser.flushOutput() 
            command = pack('<HBBBB',0x08E0, 0x00, 0x00, destination, source)
            ser.write(command)
            time.sleep(0.05)
            Rx = ser.read_all()

            if len(Rx) != 48:
                continue

            idx = Rx.find(b'\xE1\x08')
            if idx == -1:
                continue

            Rx = Rx[idx:]

            currentPos, encCount ,statusBits = unpack('<llL',Rx[8:20])
            if (statusBits & 0xF0) == 0:
                break

        print(f"The stage stops at {currentPos} nm.")
        # Flush input and output buffer
        ser.flushInput()
        ser.flushOutput() 
        return 1
    else: 
        print("MGMSG_PZMOT_GET_STATUSUPDATE: Fail to receive bytes.")
        # Flush input and output buffer
        ser.flushInput()
        ser.flushOutput() 
        return -1



if __name__ == "__main__":
    main()


