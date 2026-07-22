#import libraries
import time
import numpy as np
from astropy.io import fits
import imageio as iio

#separate into bggr components for fits compilation images (all blue frames in one, all green1 frames in one, etc.)
def bggr_separation_fits(raw_image_array):
    print(raw_image_array.shape)
    blue = raw_image_array[:,0::2, 0::2]
    print(blue.shape)
    green1 = raw_image_array[:,0::2, 1::2]
    green2 = raw_image_array[:,1::2, 0::2]
    red = raw_image_array[:,1::2, 1::2]

    return blue, green1, green2, red

#makes a fits cube image for each frame of an array of raw frames and saves it
def make_fits_cube(frames):
    print("frames shape:", frames.shape)

    frame_num = 1
    for frame in frames:
        print(f"Frame {frame_num} shape:", frame.shape)
        blue = frame[0::2, 0::2]
        print("Blue shape:", blue.shape)
        x, y = blue.shape

        array_4d = np.zeros((4, x, y), dtype=frame.dtype)
        array_4d[0] = frame[0::2, 0::2]
        array_4d[1] = frame[0::2, 1::2]
        array_4d[2] = frame[1::2, 0::2]
        array_4d[3] = frame[1::2, 1::2]
        print(array_4d.shape)
        turn_array_into_fits(array_4d, "corning_50ms_settling_time/frame" + str(frame_num))
        frame_num += 1

#turn raw image data into jpgs
def turn_array_into_jpg(frames):
    for i, frame in enumerate(frames):
        iio.imwrite(f"corning_50ms_settling_time/frame_{i}.jpg", frame)

        #use for only one image save
        #iio.imwrite(f"frame_test_50.jpg", frames[49])

#turn raw image data into pngs
def turn_array_into_png(frames: list):
    print(frames[0].dtype)
    print(frames.min())
    print(frames.max())
        
    for i, frame in enumerate(frames):
        #stretch the png for better viewing of dark images
        frame = frame.astype(np.float32)
        frame = (frame - frame.min()) / (frame.max() - frame.min())

        frame = (frame * 255).astype(np.uint8)

        iio.imwrite(f"corning_50ms_settling_time/pngs/frame_{i}.png", frame)


#turn individual color data into fits image
def turn_array_into_fits(array, title):
    #create header
    header = fits.Header()
    header['EXPTIME'] = "12000 us"
    header['Gain'] = "1.0"

    image_name = title + ".fits"
    fits.PrimaryHDU(array, header=header).writeto(image_name, overwrite=True)

#use to restructure 10bit data to be read properly
def restructure_10bit(array_8bit):
    array_10bit = []
    for frame in array_8bit:
        #print("Original:", frame.shape, frame.dtype)
        frame_10 = frame.view(np.uint16)
        array_10bit.append(frame_10)  
        #print("After view:", frame_10.shape, frame_10.dtype)      

    return np.stack(array_10bit)

def main():

    #use restructure_10bit if taking 10 bit data, if taking 8 bit data remove
    image_array = restructure_10bit(np.load("raw_frame_50msst.npy"))
    # image_array = np.load("raw_frame_nost.npy")

    #make fits cubes out of array
    make_fits_cube(image_array)
    
    #save images as jpg
    #turn_array_into_jpg(image_array)

    #save images as png
    #turn_array_into_png(image_array)
    
    image_location = "corning_50ms_settling_time/"

    #separate into bggr components for fits compilation files
    blue, green1, green2, red = bggr_separation_fits(image_array)

    #make compilation fits files from arrays
    fits_end = "_all"
    turn_array_into_fits(blue, image_location + "blue" + fits_end)
    turn_array_into_fits(green1, image_location + "green1" + fits_end)
    turn_array_into_fits(green2, image_location + "green2" + fits_end)
    turn_array_into_fits(red, image_location + "red" + fits_end)
       

main()
