import numpy as np
import cv2
import argparse
import os
from tqdm import tqdm as tqdm
import csv


def load_image(filepath):
    img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
    return img

def main():
    parser = argparse.ArgumentParser(description="Data Augmentor")
    parser.add_argument("--path", type=str, required=True)
    parser.add_argument("--annot",type=str, required=True)
    args = parser.parse_args()
    directory = args.path
    annot_file = os.path.join(directory,args.annot)
    image_directory = os.path.join(directory,"raw_images")
    new_data=[]
    with open(annot_file,'r') as f:
        reader = csv.reader(f)
        for row in tqdm(reader,desc='Augmenting Data:'):
            new_data.append(row)
            filename = row[0]
            steer = row[2]
            
            img = load_image(os.path.join(image_directory,filename)).astype(np.float32)
            bright = img + 30
            horizontal_flip_bright = bright[:, ::-1]
            dark = img - 30
            horizontal_flip_dark = dark[:, ::-1]
            horizontal_flip = img[:, ::-1]
            blured_image = cv2.GaussianBlur(img, (5,5),0)
            horizontal_flip_blur = blured_image[:, ::-1]
            
            #Horizonatl Flip             
            pre,post = filename.split('.')
            pre=pre+'_1'
            fname=pre+'.'+post
            new_steer=0-float(steer)
            new_row=[fname,row[1],str(new_steer),row[3],row[4]]
            new_data.append(new_row)
            cv2.imwrite(os.path.join(image_directory,fname),horizontal_flip)
            
            #Blurred Image   
            pre,post = filename.split('.')
            pre=pre+'_2'
            fname=pre+'.'+post
            new_row=[fname,row[1],row[2],row[3],row[4]]
            new_data.append(new_row)
            cv2.imwrite(os.path.join(image_directory,fname),blured_image)

            #Blurred Flip   
            pre,post = filename.split('.')
            pre=pre+'_3'
            fname=pre+'.'+post
            new_steer=0-float(steer)
            new_row=[fname,row[1],str(new_steer),row[3],row[4]]
            new_data.append(new_row)
            cv2.imwrite(os.path.join(image_directory,fname),horizontal_flip_blur)

            #Bright
            pre,post = filename.split('.')
            pre=pre+'_3'
            fname=pre+'.'+post
            new_row=[fname,row[1],row[2],row[3],row[4]]
            new_data.append(new_row)
            cv2.imwrite(os.path.join(image_directory,fname),bright)

            #Bright Flip
            pre,post = filename.split('.')
            pre=pre+'_5'
            fname=pre+'.'+post
            new_steer=0-float(steer)
            new_row=[fname,row[1],str(new_steer),row[3],row[4]]
            new_data.append(new_row)
            cv2.imwrite(os.path.join(image_directory,fname),horizontal_flip_bright)

            #Dark
            pre,post = filename.split('.')
            pre=pre+'_6'
            fname=pre+'.'+post
            new_row=[fname,row[1],row[2],row[3],row[4]]
            new_data.append(new_row)
            cv2.imwrite(os.path.join(image_directory,fname),dark)

            #Dark Flip
            pre,post = filename.split('.')
            pre=pre+'_7'
            fname=pre+'.'+post
            new_steer=0-float(steer)
            new_row=[fname,row[1],str(new_steer),row[3],row[4]]
            new_data.append(new_row)
            cv2.imwrite(os.path.join(image_directory,fname),horizontal_flip_dark)

    with open(annot_file,'w') as f:
        writer = csv.writer(f)
        writer.writerows(new_data)              
            
if __name__ == '__main__':
    main()