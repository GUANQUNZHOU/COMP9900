#!/usr/bin/python

from flask import Flask
from flask_login import LoginManager
import os, pyrebase
from app import models
# from app.extraction.nlpModule import ConsecutiveNPChunkTagger,ConsecutiveNPChunker
# from app.extraction import nlpOperation, nlpModule, schemaExtraction

# Initialize the environment and connection to Firebase
config = {
	"apiKey": "AIzaSyCvZiWJAD9pac9LHACfsKupXAAvyN7INAk",
    "authDomain": "gank-5502c.firebaseapp.com",
    "databaseURL": "https://gank-5502c.firebaseio.com",
    "projectId": "gank-5502c",
    "storageBucket": "gank-5502c.appspot.com",
    "messagingSenderId": "591295625571",
    "appId": "1:591295625571:web:8c5fd9f70d0c46b839fb56",
    "measurementId": "G-R9MGVMM9S0"
}
firebase = pyrebase.initialize_app(config)
db = firebase.database()

application = Flask(__name__)
logman = LoginManager(application)
logman.login_view = '/'
logman.login_message = 'Access denied. Please login first.'

manager = models.Manager(db)
manager.setup_email('ctcagank@gmail.com', 'Gank1234')

@logman.user_loader
def load_user(userid):
    return manager.get(userid)


from app import routes
from app import extraction
from app.extraction import schemaExtraction