import cv2
import datetime

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


def calculate_video_duration(video_path):
    # create video capture object
    data = cv2.VideoCapture(video_path)
    # count the number of frames
    frames = data.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = int(data.get(cv2.CAP_PROP_FPS))
    # calculate dusration of the video
    seconds = int(frames / fps)
    video_time = str(datetime.timedelta(seconds=seconds))
    # print("duration in seconds:", seconds)
    # print("video time:", video_time)
    return seconds


calculate_video_duration("static/uploads/video.mp4")