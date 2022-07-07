import cv2

def video_thumbnail(video_path,image_path):
    vidcap = cv2.VideoCapture(video_path)
    success,image = vidcap.read()
    count = 0
    while success:
        if count == 50:
            filename = image_path+".png"
            cv2.imwrite(filename, image) 
        success,image = vidcap.read()
        count += 1
    return filename
