# capstone-project-gank
Project 4: Intelligent Assistant for electronic Logbook in Radiology training
----------------
Developed By: GANK
-----------------
GIthub: https://github.com/comp3300-comp9900-term-3-2019/capstone-project-gank
-----------------
If you want to run our backend for checking if it works, please check the first section ***For Tutors***.
If you want to use our product, please ignore the first section and check the second section ***How to use***.
## For Tutors
To run our backend, you will need:
### Prerequisite
#### Download packages:
1. Download datasets from nltk using `nltk.download()`
2. Download glove word embedding using the link  `https://nlp.stanford.edu/data/glove.6B.zip` and put it under [Training Requirment](./backend/app/training_requirements/)
3. Download [ngrok](https://ngrok.com/) if you dont have it installed. Then run `./ngrok http 5000`
4. Download [env](./Dialogflow/env) this virtual environment file ***It is too large we can't submit***
#### Set up Environments:
1. All required libraries are located in [Required Libaraies](./requirements.txt). You may choose to install missing libraries or use the setup environment by cd to [Dialogflow](./Dialogflow/) and run `source env/bin/activate` to activate this environment `env`
2. Copy the generated address from ngrok and paste it to replace the current address in `Hyper-parameters` under [routes](./backend/app/routes.py). However, you need to contact Thomas `thomascong@outlook.com` to change webhook routes from Dialogflow console in order to connect Dialogflow agent to your generated address. :sob:
#### How to run:
cd to [backend](./backend) and type `python3 backend.py` to run.

## How to use
Our service is held on `http://a161b893.ngrok.io`, connect to this website and enjoy using it!
### Note:
As our backend is currently deployed on our own device and we achieve Intranet penetration using ngrok. if there are any issues, please contact `ctcagank@gmail.com`or `thomascong@outlook.com` 
