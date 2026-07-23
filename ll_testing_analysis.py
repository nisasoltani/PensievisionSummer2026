"""
This code provides a number of functions to compare arrays of images. 
"""

#import libraries
import numpy as np
import matplotlib.pyplot as plt
import cv2
from pathlib import Path
from scipy.stats import ttest_ind
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression

#separate into bggr components for fits compilation images (all blue frames in one, all green1 frames in one, etc.)
def bggr_separation_fits(raw_image_array):
    #print(raw_image_array.shape)
    blue = raw_image_array[:,0::2, 0::2]
    #print(blue.shape)
    green1 = raw_image_array[:,0::2, 1::2]
    green2 = raw_image_array[:,1::2, 0::2]
    red = raw_image_array[:,1::2, 1::2]

    return blue, green1, green2, red

#find the sharpest image in a dataset using the tenengrad test
def find_sharpest_image_tenengrad(array):
    sharpest_image = array[0].astype(np.float32)
    sharpest_image_number = 0
    for i in range(0, len(array)):
        image = array[i].astype(np.float32)
        gx_sharpest = cv2.Sobel(sharpest_image, cv2.CV_32F, 1, 0, ksize=3)
        gy_sharpest = cv2.Sobel(sharpest_image, cv2.CV_32F, 0, 1, ksize=3)
        sharpest_image_score = np.mean(gx_sharpest**2 + gy_sharpest**2)

        gx_image = cv2.Sobel(image, cv2.CV_32F, 1, 0, ksize=3)
        gy_image = cv2.Sobel(image, cv2.CV_32F, 0, 1, ksize=3)
        image_score = np.mean(gx_image**2 + gy_image**2)

        if sharpest_image_score < image_score:
            sharpest_image = image
            sharpest_image_number = i
    
    return sharpest_image, sharpest_image_number

#find the sharpest image in an array of images using the laplacian       
def find_sharpest_image_laplacian(array):
    sharpest_image = array[0]
    sharpest_image_number = 0
    for i in range(0, len(array)):
        image = array[i].astype(np.float32)
        sharpest_image_score = cv2.Laplacian(sharpest_image, cv2.CV_32F).var()
        image_score = cv2.Laplacian(image, cv2.CV_32F).var()
        if sharpest_image_score < image_score:
            sharpest_image = image
            sharpest_image_number = i
    
    return sharpest_image, sharpest_image_number

#find sharpest image in array using the gradient
def find_sharpest_image_gradient(array):
    scores = []
    for image in array:
        gy, gx = np.gradient(image)
        gnorm = np.sqrt(gx**2 + gy**2)
        sharpness = np.average(gnorm)
        scores.append(sharpness)
    
    print(np.mean(scores), np.std(scores))
    
    plt.plot(scores)
    plt.xlabel("Frame")
    plt.ylabel("Sharpness score")
    plt.show()

#calculate the amount of dots in an image
def get_dot_amount(image):
    _, thresh = cv2.threshold(image, 100, 255, cv2.THRESH_BINARY_INV)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(thresh)
    dot_centers = centroids[1:]
    print(len(dot_centers))

#create plot from sharpness score
def sharpness_plot(array):
    scores = []
    for i in range(len(array)):
        gx = cv2.Sobel(array[i], cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(array[i], cv2.CV_32F, 0, 1, ksize=3)

        score = np.mean(gx**2 + gy**2)

        scores.append(score)

    print(np.mean(scores), np.std(scores))

    plt.plot(scores)
    plt.xlabel("Frame")
    plt.ylabel("Sharpness score")
    plt.show()

#use to restructure 10bit data to be read properly
def restructure_10bit(array_8bit):
    array_10bit = []
    for frame in array_8bit:
        #print("Original:", frame.shape, frame.dtype)
        frame_10 = frame.view(np.uint16)
        array_10bit.append(frame_10)  
        #print("After view:", frame_10.shape, frame_10.dtype)      

    return np.stack(array_10bit)

#measure the distortion of an image and return the rms value
def dot_distortion_rms(image):
    green = image[0::2, 1::2]

    #normalize to 8-bit
    gray = cv2.normalize(green, None, 0, 255, cv2.NORM_MINMAX)
    gray = gray.astype(np.uint8)

    #detect blobs
    params = cv2.SimpleBlobDetector_Params()
    params.filterByArea = True
    params.minArea = 7
    params.maxArea = 5000

    detector = cv2.SimpleBlobDetector_create(params)

    #find dot centers
    keypoints = detector.detect(gray)
    dot_centers = np.array([kp.pt for kp in keypoints])

    # print(f"Detected {len(dot_centers)} dots")

    # print("dot_centers shape:", dot_centers.shape)
    # print(dot_centers[:10])

    #sort rows appropriately given the slight distortion of the image
    pca = PCA(n_components=2)
    pca.fit(dot_centers)

    # First component = horizontal grid direction
    x_axis = pca.components_[0]

    # Second component = vertical grid direction
    y_axis = pca.components_[1]

    # print("x axis:", x_axis)
    # print("y axis:", y_axis)

    grid_x = dot_centers @ x_axis
    grid_y = dot_centers @ y_axis

    #sort rows from top to bottom
    row_order = np.argsort(grid_y)


    row_sizes = [13] + [17]*9

    rows = []

    start = 0

    for size in row_sizes:
        indices = row_order[start:start+size]

        #sort dots left to right along the grid direction
        indices = indices[np.argsort(grid_x[indices])]

        rows.append(dot_centers[indices])

        start+=size

    # for i, row in enumerate(rows):
    #     print(f"Row {i}: {len(row)}")

    # for i,row in enumerate(rows):
    #     print(i, np.mean(row @ y_axis))

    #calculate horizontal spacing
    horizontal_spacing = []
    for row in rows:
        x_positions = row @ x_axis
        x_positions = np.sort(x_positions)

        horizontal_spacing.append(np.diff(x_positions))

    #print(horizontal_spacing)

    #calculate vertical spacing
    vertical_spacing = []
    for i in range(len(rows) - 1):
        upper = rows[i]
        lower = rows[i + 1]

        upper_y = upper @ y_axis
        lower_y = lower @ y_axis

        n = min(len(upper_y), len(lower_y))

        vertical_spacing.append(lower_y[:n] - upper_y[:n])

    #calculate the mean spacing for each axis
    mean_horizontal = np.mean(np.concatenate(horizontal_spacing))
    mean_vertical = np.mean(np.concatenate(vertical_spacing))

    #calculate the relative error
    horizontal_error = [
        (row - mean_horizontal) / mean_horizontal
        for row in horizontal_spacing
    ]

    vertical_error = [
        (row - mean_vertical) / mean_vertical
        for row in vertical_spacing
    ]

    #calculate rms distortion
    errors = np.concatenate([np.concatenate(horizontal_error), np.concatenate(vertical_error)])
    rms = np.sqrt(np.mean(errors**2))

    return rms

#read the space between two dots in an image if you already know the rows and columns
def read_dots_findCirclesGrid(image, columns, rows):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    pattern_size = (columns, rows)

    found, centers = cv2.findCirclesGrid(gray_image, pattern_size, flags=cv2.CALIB_CB_SYMMETRIC_GRID)
    # print("Found grid:", found)

    if found:
        #print("Number of centers:", len(centers))
        # image_draw = image.copy()
        # cv2.drawChessboardCorners(
        #     image_draw,
        #     pattern_size,
        #     centers,
        #     found
        # )

        # plt.imshow(cv2.cvtColor(image_draw, cv2.COLOR_BGR2RGB))
        # plt.show()

        centers = centers.reshape(-1, 2)
        
        rows, cols = pattern_size[1], pattern_size[0]
        
        horizontal = np.zeros((rows, cols-1))



        for r in range(rows):
            row_centers = centers[r*cols:(r+1)*cols]

            for c in range(cols-1):
                horizontal[r,c] = row_centers[c+1, 0] - row_centers[c, 0]

        
        vertical = np.zeros((rows-1, cols))

        for r in range(rows-1):
            for c in range(cols):
                top = centers[r*cols+c]
                bottom = centers[(r+1)*cols+c]

                vertical[r, c] = bottom[1] - top[1]

        
        # np.set_printoptions(precision=2, suppress=True)
        # print("Horizontal Spacing:", horizontal)
        # print("\nVertical Spacing:", vertical)

        # np.savetxt("horizontal_spacing.csv", horizontal, fmt="%.2f")
        # np.savetxt("vertical_spacing.csv", vertical, fmt="%.2f")

#take two arrays of images, find the mean rms of the reference images, compare 
#all other images to the reference mean and perform a ttest to see if there's a difference
#between the reference images and the test images
def perform_rms_ttest(reference_array, test_array):
    reference_mean = np.mean(reference_array, axis=0)

    reference_rms = []
    for i in range(len(reference_array)):
        mean_image = np.mean(
            np.delete(reference_array, i, axis=0),
         axis=0
        )

        diff = reference_array[i].astype(np.float32) - mean_image

        reference_rms.append(
            np.sqrt(np.mean(diff**2))
        )
    # for image in reference_array:
    #     diff = image.astype(np.float32) - reference_mean
    #     rms = np.sqrt(np.mean(diff**2))
    #     reference_rms.append(rms)
    
    # print("Reference RMS:", reference_rms)

    test_rms = []
    for image in test_array:
        diff = image.astype(np.float32) - reference_mean
        rms = np.sqrt(np.mean(diff**2))
        test_rms.append(rms)
    
    print("Test RMS:", test_rms)

    t_stat, p_value = ttest_ind(reference_rms, test_rms, equal_var=False)

    print("t =", t_stat)
    print("p =", p_value)

def measure_brightness(image_array):
     image_brightness = []

     for image in image_array:
        image_brightness.append(np.std(image))

     return np.array(image_brightness)

def main():
    #finding the sharpest image of all the arrays
    directory = Path("liquid-lens-testing")

    reference_images = []
    test_images = []

    brightness_array = []

    for file in directory.iterdir():
        if file.is_file() and file.name.startswith("ll_3d_darknesstest"):
            image_array = restructure_10bit(np.load(file))
            #roi = image_array[:,200:400, 300:600]
            # blue, green1, green2, red = bggr_separation_fits(image_array)
            # image, number = find_sharpest_image_tenengrad(green1)
            # if "ref" in file.name:
            #     reference_images.append(image)
            # else:
            #     test_images.append(image)
            
            # print(file.name, number)

            block_brightness = []
            for image in image_array:
                blocks = view_as_blocks(image, block_shape=(96,96))
                block_brightness.append(np.mean(blocks, axis=(2,3)))
            
            block_brightness = np.array(block_brightness)

            fig, axes = plt.subplots(14, 15, figsize=(15, 14))

            reference = block_brightness[0]

            vmin = np.min(block_brightness - reference)
            vmax = np.max(block_brightness - reference)

            for i, ax in enumerate(axes.flat):
                if i < len(block_brightness):
                    im = ax.imshow(block_brightness[i] - reference,
                                cmap='bwr',
                                vmin=vmin,
                                vmax=vmax)
                    ax.set_title(f"{i+1}", fontsize=6)
                    ax.axis("off")
                else:
                    ax.axis("off")

            fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.8)
            plt.show()

            #brightness_array.append(measure_brightness(image_array))

    # for set_num, brightness in enumerate(brightness_array, start=1):
    #     #brightness = brightness[10:]
    #     darkest = np.argmin(brightness)

    #     print(f"Set {set_num}:")
    #     print(f" Darkest image = {darkest}")
    #     print(f" Median brightness = {brightness[darkest]:.2f}")
    


    # plt.figure(figsize=(8, 6))

    # for i, profile in enumerate(brightness_array):
    #     plt.plot(profile, label=f"Set {i+1}")

    # plt.xlabel("Image Number")
    # plt.ylabel("Brightness Standard Deviation")
    # plt.title("Brightness Profiles")
    # #plt.savefig('liquid-lens-testing/brightness-analysis/pyramid_brightnessstd_fullimage.png')
    # plt.legend()
    # plt.show()

   
    # #print(np.shape(reference_images))

    # reference_images = np.array(reference_images)
    # test_images = np.array(test_images)

    # reference_rms = []
    # #find distortion for reference images
    # for image in reference_images:
    #     rms = dot_distortion_rms(image)
    #     #print(rms)
    #     reference_rms.append(rms)

    # #print("\n")

    # #find distortion for test images
    # test_rms = []
    # for image in test_images:
    #     rms = dot_distortion_rms(image)
    #     #print(rms)
    #     test_rms.append(rms)

    
    # t_stat, p_value = ttest_ind(reference_rms, test_rms, equal_var=False)

    # print("t =", t_stat)
    # print("p =", p_value)
    
    #check for duplicate images
    # for i, ref in enumerate(reference_images):
    #     for j, test in enumerate(test_images):
    #         if np.array_equal(ref, test):
    #             print(f"Reference {i} is identical to Test {j}")

    #perform_rms_ttest(reference_images, test_images)
    



    #plot one array
    # image_array = restructure_10bit(np.load("raw-frames/raw_frame_50msst.npy"))
    # blue, green1, green2, red = bggr_separation_fits(image_array)
    # find_sharpest_image_gradient(green1)

    #testing equivalence of two arrays
    # reference = np.load("ll_test_ref1.npy")
    # test = np.load("ll_test_test2.npy")
    # subtract_arrays(reference, test)

    #find the distance between dots
    # image = np.load("liquid-lens-testing.npy")
    # read_dots(image, 14, 18)

    #array_equal(np.load("raw-frames/raw_frame_wlight_10gain.npy"))

main()
