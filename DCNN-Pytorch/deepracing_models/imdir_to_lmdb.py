import numpy as np
import data_loading.backend
import os
import argparse
import skimage
import skimage.io
import shutil
import imutils
import cv2
from functools import partial
def extractROI(x, y, w, h, image):
    return image[y:y+h, x:x+w].copy()
def main():
    parser = argparse.ArgumentParser(description="Load an image directory into a database")
    parser.add_argument("image_dir", type=str, help="Directory containing the images")
    parser.add_argument("imrows", type=int, help="Number of rows to resize images to")
    parser.add_argument("imcols", type=int, help="Number of cols to resize images to")
    parser.add_argument("--display_resize_factor", type=float, default=0.5, help="Resize the first image by this factor for selecting a ROI.")
    parser.add_argument('-R','--ROI', nargs='+', help='ROI to capture', default=None)
    args = parser.parse_args()
    img_folder = args.image_dir
    keys = [fname for fname in  os.listdir(img_folder) if os.path.isfile(os.path.join(img_folder,fname)) and os.path.splitext(fname)[1]==".jpg"]
    img_files = [os.path.join(img_folder, key) for key in keys]
    im_size = None
    imrows = args.imrows
    imcols = args.imcols
    roi = args.ROI
    im = imutils.readImage(img_files[0])
    if roi is not None:
        assert(len(roi) == 4)
        f = partial(extractROI,int(roi[0]),int(roi[1]),int(roi[2]),int(roi[3]))
    else:    
        factor = args.display_resize_factor
        windowname = "Test Image"
        cv2.namedWindow(windowname,cv2.WINDOW_AUTOSIZE)
        x_,y_,w_,h_ = cv2.selectROI(windowname, cv2.cvtColor(imutils.resizeImageFactor(im,factor), cv2.COLOR_RGB2BGR), showCrosshair =True)
        print((x_,y_,w_,h_))
        x = int(round(x_/factor))
        y = int(round(y_/factor))
        w = int(round(w_/factor))
        h = int(round(h_/factor))
        print((x,y,w,h))
        f = partial(extractROI,x,y,w,h)
        cv2.imshow(windowname, cv2.cvtColor(f(im), cv2.COLOR_RGB2BGR))
        cv2.waitKey(0)
        cv2.destroyWindow(windowname)
    im_size = np.array((imrows, imcols, im.shape[2]))
    dbpath = os.path.join(img_folder,"lmdb")
    if(os.path.isdir(dbpath)):
        s=""
        while not (s=='n' or s=='y'):
            s=input("Database folder " + dbpath+ " already exists. overwrite with new data? [y/n]\n")
        if(s=='n'):
            print("Goodbye then!")
            exit(0)
        shutil.rmtree(dbpath)
    db = data_loading.backend.LMDBWrapper()
    db.readImages(img_files, keys, dbpath, im_size, func=f)
if __name__ == '__main__':
  main()
