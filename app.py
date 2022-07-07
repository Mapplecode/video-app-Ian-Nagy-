from tkinter.messagebox import QUESTION
from flask import Flask,render_template,session,redirect,request,flash,url_for,Response
# from flask_paginate import Pagination, get_page_args
from flask_session import Session
from functools import wraps
import pymongo,time
from datetime import datetime
from passlib.hash import pbkdf2_sha256
import uuid, os
from opencvoperation import *


# ==========================================================
import cv2
import time
import os, sys
import numpy as np
from threading import Thread
global capture,rec_frame, grey, switch, neg, face, rec, out 
capture=0
grey=0
neg=0
face=0
switch=1
rec=0

#Load pretrained face detection model    
net = cv2.dnn.readNetFromCaffe('./saved_model/deploy.prototxt.txt', './saved_model/res10_300x300_ssd_iter_140000.caffemodel')

# camera = cv2.VideoCapture(0)

def record(out):
    global rec_frame
    while(rec):
        time.sleep(0.05)
        out.write(rec_frame)


def detect_face(frame):
    global net
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0,
        (300, 300), (104.0, 177.0, 123.0))   
    net.setInput(blob)
    detections = net.forward()
    confidence = detections[0, 0, 0, 2]

    if confidence < 0.5:            
            return frame           

    box = detections[0, 0, 0, 3:7] * np.array([w, h, w, h])
    (startX, startY, endX, endY) = box.astype("int")
    try:
        frame=frame[startY:endY, startX:endX]
        (h, w) = frame.shape[:2]
        r = 480 / float(h)
        dim = ( int(w * r), 480)
        frame=cv2.resize(frame,dim)
    except Exception as e:
        pass
    return frame
 

def gen_frames(camera):  # generate frame by frame from camera
    global out, capture,rec_frame
    while True:
        success, frame = camera.read() 
        if success:
            if(face):                
                frame= detect_face(frame)
            if(rec):
                rec_frame=frame
                frame= cv2.putText(cv2.flip(frame,1),"Recording...", (0,25), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255),4)
                frame=cv2.flip(frame,1)
            try:
                ret, buffer = cv2.imencode('.jpg', cv2.flip(frame,1))
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            except Exception as e:
                pass
                
        else:
            pass
# ==========================================================
app = Flask(__name__,static_url_path='/static')
app.secret_key = b'\xcc^\x91\xea\x17-\xd0W\x03\xa7\xf8J0\xac8\xc5'
app.config['SESSION_TYPE'] = 'filesystem'
# Database
client = pymongo.MongoClient('localhost', 27017)
# collection name
db = client.videoDB

# Decorators
def login_required(f):
  @wraps(f)
  def wrap(*args, **kwargs):
    if 'logged_in' in session:
      return f(*args, **kwargs)
    else:
      return redirect('/login')
  
  return wrap

@app.route("/")
def home():
	return render_template("home.html")

@app.route("/login",methods=['GET','POST'])
def login():
	if request.method == 'POST':
		user = db.users.find_one({
		"email": request.form.get('email')
		})
		if user['email'] == "admin@localhost.com":
			del user['password']
			session['logged_in'] = True
			session['user'] = user			
			return redirect('admindashboard')

		if user and pbkdf2_sha256.verify(request.form.get('password'), user['password']):
			if user['status'] == "active":
				del user['password']
				session['logged_in'] = True
				session['user'] = user
				return redirect('dashboard')
			else:
				print("[INFO] User account is deactivated.")
	return render_template("login.html")

@app.route("/register",methods=['GET','POST'])
def register():
	if request.method == 'POST':
		# Create the user object
		user = {
		"_id": uuid.uuid4().hex,
		"name": request.form.get('name'),
		"email": request.form.get('email'),
		"password": request.form.get('password'),
		"role": "user",
		"status" : "active",
		"created_at": datetime.now()
		}

		# Encrypt the password
		user['password'] = pbkdf2_sha256.encrypt(user['password'])
		# Check for existing email address
		if db.users.find_one({ "email": user['email'] }):
			flash('Email address already in use.')
		else:
			db.users.insert_one(user)
			del user['password']
			session['logged_in'] = True
			session['user'] = user	
			return redirect('dashboard')
	return render_template("register.html")

@app.route("/logout",methods=['POST'])
def logout():
	if request.method == 'POST':
		session.clear()
		return redirect('/')



@app.route("/dashboard",methods=['GET','POST'])
@login_required
def dashboard():
	dashboard_name = "Video Dashboard"
	return render_template("dashboard/admin/dashboard.html",dashboard_name=dashboard_name,user=session["user"])

@app.route("/allvideos",methods=['GET','POST'])
@login_required
def all_videos():
	return render_template("dashboard.html")


@app.route("/admindashboard",methods=['GET','POST'])
@login_required
def admin_dashboard():
	if request.method == "POST":
		creating = request.form.get("projectname")
		# return redirect("createproject")
		return redirect(url_for('.create_project', creating=creating))
	dashboard_name = "Admin Dashboard"
	return render_template("dashboard/admin/admindashboard.html",dashboard_name=dashboard_name)
# =========================( USERS )================================================
@app.route("/userdata",methods=['GET'])
@login_required
def userdata():
	dashboard_name = "Admin Dashboard"
	userdata = db.users.find()
	return render_template("dashboard/admin/users/userdata.html",dashboard_name=dashboard_name,userdata=userdata)

@app.route("/createuser",methods=['GET','POST'])
@login_required
def createuser():
	dashboard_name = "Admin Dashboard"
	if request.method == "POST":
		name = request.form.get("username")
		email = request.form.get("email")
		status = request.form.get("status")
		password = request.form.get("password")
		role = request.form.get("role")
		if not db.users.find_one({"email":email}):
			insert_user = {
					"_id": uuid.uuid4().hex,
					"name": name,
					"email": email,
					"status": status,
					"role":role,
					"password" : pbkdf2_sha256.encrypt(password),
					"created_at" : datetime.today(),
					"updated_at" : "null"
			}
			db.users.insert_one(insert_user)
			return redirect(url_for("userdata"))
		else:
			flash("Email already exists.")
	return render_template("dashboard/admin/users/createuser.html",dashboard_name=dashboard_name)

@app.route("/userdataedit/<id>",methods=['GET','POST'])
@login_required
def userdataedit(id):
	dashboard_name = "Admin Dashboard"
	userdata = db.users.find_one({ "_id": id })
	if request.method == "POST":
		name = request.form.get("username")
		email = request.form.get("email")
		status = request.form.get("status")
		update_user = {
				"name": name,
				"email": email,
				"status": status,
				"updated_at" : datetime.today()
		}
		db.users.find_one_and_update({"_id": id}, 
									{"$set": update_user})
		return redirect(url_for("userdata"))
	return render_template("dashboard/admin/users/userdataedit.html",dashboard_name=dashboard_name,userdata=userdata)

@app.route("/userdetails/<id>",methods=["GET"])
def userdetails(id):
	dashboard_name = "Admin Dashboard"
	userdata = db.users.find_one({"_id":id})
	feedback = list(db.feedback.find())
	thisfeedback = list()
	for item in feedback:
		if 'user_info' in item:
			if item['user_info']['_id'] == id:
				thisfeedback.append(item)
	return render_template("dashboard/admin/users/userdetails.html",dashboard_name=dashboard_name,userdata=userdata,feedback=thisfeedback)


@app.route("/createproject",methods=['GET','POST'])
@login_required
def create_project():
	project_name = request.args['creating']
	if request.method == "POST":
		if request.files['file']:
			file = request.files['file']
			file_extenion = (file.filename.split('.')[-1]).upper()
			if file_extenion == "MP4" or file_extenion == "MOV" or file_extenion == "FLV" or file_extenion == "WMV" or file_extenion == "MKV":
				if os.path.exists('static/uploads'):
					destination = 'static/uploads/'+file.filename
					file.save(destination)
				else:
					parent_dir = os.getcwd() + '\static'
					path = os.path.join(parent_dir, 'uploads')				
					os.mkdir(path)
					destination = 'static/uploads/'+file.filename
					file.save(destination)

				image_ = 'static/thumbnails/'+file.filename.split(".")[0]
				location = video_thumbnail(video_path=destination,image_path=image_)
				# create project
				pid = uuid.uuid4().hex
				projectdata = {
					"_id": pid,
					"projectname": project_name
				}

				db.project.insert_one(projectdata)
				
				# Create the video object
				video = {
				"_id": uuid.uuid4().hex,
				"title": request.form.get('title'),
				"projectinfo": {"id":pid,"projectname":project_name},
				"category": request.form.get('category'),
				"description": request.form.get('description'),
				"filename": destination,
				"thumbnail": location,
				"created_at": datetime.today()
				}
				# insert int videos table
				db.videos.insert_one(video)
				flash("File upload successfully,succ")
			else:
				flash("Invaild extension system allow 	MP4, MOV, FLV, MKV, WMV only these extentions.,warn")
		
	dashboard_name = "Admin Dashboard"

	return render_template("dashboard/admin/projects/createproject.html",dashboard_name=dashboard_name,project_name=project_name)


@app.route("/allvideo",methods=["GET"])
@login_required
def all_video():
	dashboard_name = "Admin Dashboard"
	all_videos = db.videos.find()
	return render_template("dashboard/admin/allvideos.html",dashboard_name=dashboard_name,videodata=all_videos)




@app.route("/video/<id>",methods=["GET","POST"])
@login_required
def single_video(id):
	dashboard_name = "Admin Dashboard"
	single_video = db.videos.find_one({ "_id": id })
	user_feedback = db.feedback.find({"videoId":id})
	return render_template("dashboard/admin/singlevideo.html",dashboard_name=dashboard_name,video=single_video,feedback=user_feedback)


#===================== (questions) ===============
@app.route("/allquetions",methods=["GET","POST"])
@login_required
def all_que():
	dashboard_name = "Admin Dashboard"
	all_questions = db.questions.find()
	return render_template("dashboard/admin/questions/allquestions.html",dashboard_name=dashboard_name,questionsdata=all_questions)

@app.route("/createquestion",methods=["GET","POST"])
@login_required
def create_qa():
	dashboard_name = "Admin Dashboard"
	if request.method == "POST":
		question = request.form.get("question")
		note = request.form.get("note")
		status = request.form.get("status")
		ins_question = {
				"_id": uuid.uuid4().hex,
				"question": question,
				"note": note,
				"status": status,
				"created_at" : datetime.today(),
				"updated_at" : 'null'
				}
		db.questions.insert_one(ins_question)
		return redirect(url_for("all_que"))
	return render_template("dashboard/admin/questions/createquestion.html",dashboard_name=dashboard_name)

@app.route("/updatequetion/<id>",methods=["GET","POST"])
@login_required
def update_qa(id):
	dashboard_name = "Admin Dashboard"
	current_que = db.questions.find_one({ "_id": id })
	if request.method == "POST":
		question = request.form.get("question")
		note = request.form.get("note")
		status = request.form.get("status")
		update_question = {
				"question": question,
				"note": note,
				"status": status,
				"updated_at" : datetime.today()

		}
		db.questions.find_one_and_update({"_id": id}, 
									{"$set": update_question})
		return redirect(url_for("all_que"))
	return render_template("dashboard/admin/questions/updatequestion.html",dashboard_name=dashboard_name,questionsdata=current_que)

@app.route("/delete/<id>",methods=["POST"])
@login_required
def delete(id):
	if request.method == "POST":
		if db.questions.find_one({"_id":id}):
			db.questions.delete_one({"_id": id })
			return redirect(url_for("all_que"))

		elif db.users.find_one({"_id":id}):
			db.users.delete_one({"_id": id })
			return redirect(url_for("userdata"))

@app.route("/questionsfeedback",methods=["POST"])
@login_required
def feedback_qa():
	if request.method == "POST":
		# ins_feedback = {
		# 		"_id": uuid.uuid4().hex,
		# 		"data": dict(request.form),
		# 		"user_info" : {"_id":session['user']["_id"],"email" : session['user']["email"]},
		# 		"created_at": datetime.today()
		# 		}
		res_data = dict(request.form)
		if "videoId" in list(res_data.keys()):
			video_id = res_data["videoId"]
			res_data.pop("videoId")

		ins_feedback = {
				"_id": uuid.uuid4().hex,
				"data": res_data,
				"videoId" : video_id,
				"created_at": datetime.today()
				}
		db.feedback.insert_one(ins_feedback)
		return {"data":"success"}


#===================== (end) ===============

@app.route("/video/watch/<id>",methods=["GET","POST"])
def watch_video(id):
	dashboard_name = "WATCH | "
	single_video = db.videos.find_one({ "_id": id })
	all_questions = list(db.questions.find())
	return render_template("dashboard/watchvideo.html",dashboard_name=dashboard_name,video=single_video,questionsdata=all_questions)

@app.route("/start/cam",methods=["POST"])
def start_Cam():
	global switch,camera
	if request.method == "POST":
		# frame_width = int(cap.get(3))
		# frame_height = int(cap.get(4))
		# video_cod = cv2.VideoWriter_fourcc(*'XVID')
		# video_output= cv2.VideoWriter('captured_video.avi',
		# 					video_cod,
		# 					10,
		# 					(frame_width,frame_height))
		if request.form.get("status") == "start":
			camera = cv2.VideoCapture(0)
			gen_frames(camera)
			global rec, out
			rec = not rec
			if(rec):
				now=datetime.now() 
				# fourcc = cv2.VideoWriter_fourcc(*'XVID')
				fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
				out = cv2.VideoWriter('./videostore/vid_{}.mp4'.format(str(now).replace(":",'')), fourcc, 20.0, (640, 480))
				#Start new thread for recording the video
				thread = Thread(target = record, args=[out,])
				thread.start()
			elif(rec==False):
				out.release()
		# 	while(True):
		# 		ret, frame = cap.read()
		# 		if ret == True: 
		# 			video_output.write(frame)
		# 			cv2.imshow('frame',frame)
		# 			if cv2.waitKey(1) & 0xFF == ord('x'):
		# 				break
		# 		else:
		# 			break  
			print("The video was successfully saved")
			return {"test":"success"}
		elif request.form.get("status") == "stop":
			# cap.release()
			# video_output.release()
			# cv2.destroyAllWindows()
			return {"test":"success"} 

#================================(Project)==================================

@app.route("/allprojects",methods=["GET","POST"])
def allprojects():
	dashboard_name = "Admin Dashboard"
	projectdata = db.project.find()
	return render_template("dashboard/admin/projects/allprojects.html",dashboard_name=dashboard_name,pdata=projectdata)

@app.route("/projectdetails/<id>",methods=["GET","POST"])
def projectdetailview(id):
	dashboard_name = "Admin Dashboard"
	projectdata = db.project.find_one({"_id":id})
	videodata = db.videos.find({"projectinfo.id":id})
	return render_template("dashboard/admin/projects/projectdetailview.html",dashboard_name=dashboard_name,pdata=projectdata,videodata=videodata)

if __name__ == "__main__":
	app.run()

