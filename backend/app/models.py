#!/usr/bin/python
from flask_login import UserMixin
from datetime import date, datetime
import re, xlwt
from collections import OrderedDict
from werkzeug.security import generate_password_hash, check_password_hash
from app.extraction import schemaExtraction
import smtplib
import imghdr
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import random

class User(UserMixin):
    """ Simple class for individual user """
    def __init__(self, id=None, u=None):
        # super(User, self).__init__()
        # u: user info list sorted as [email, name, paswrd, phone]
        self.id = id
        if u is not None:
            self.email = u.get('User_email_address')
            self.name  = u.get('User_name')
            # self.pswd  = u['User_password']
            self.phone = u.get('User_phone_number')
        else:
            print('[ERROR] Failed loading user info!')

class Manager():
    """ The user manager class with database access """
    def __init__(self, db):
        # fetch user data from database
        self.db = db
        self.db_user = db.child("User").get().val()
        self.uids = list(self.db_user.keys())
        users = list(self.db_user.values())

        self.names = [i.get('User_name') for i in users]
        # self.pswds = [i['User_password'] for i in users]
        self.emails = [i.get('User_email_address') for i in users]
        self.phones = [i.get('User_phone_number') for i in users]
        self.pswds = [i.get('Real_password') for i in users]
    
        self.bkup_name = '_backup'
        self.lb_type = {'cert':     'Certification',             # LvA - 150, LvB - 300
                        'recert1':  'Recertification_Pathway1',  # LvA - 300, LvB - 600
                        'recert2':  'Recertification_Pathway2',  # LvA - 300, LvB - 600
                        'conv':     'Conversion' }               # x recert + 150 

    # password hashing
    def _set_password(self, password):
        return generate_password_hash(password)
    def _check_password(self, uid, password):
        pswd_hash = self.db.child("User").child(uid).child('User_password').get().val()
        return check_password_hash(pswd_hash, password)

    def setup_email(self, address, password):
        self.email_address = address
        self.email_password = password

    def _send_email(self, recipient, subj, content=None):
        if None in [self.email_address, self.email_password, recipient, subj]:
            return False
        # msg = EmailMessage()
        msg = MIMEMultipart('alternative')
        msg['From'] = self.email_address
        msg['Subject'] = subj
        msg['To'] = recipient
        # msg.set_content(content)
        html_content = MIMEText(content, 'html')
        msg.attach(html_content)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(self.email_address, self.email_password)
            smtp.send_message(msg)
        return True

    def _update_records(self):
        """ Updates user info stored in manager object """
        abc = self.db.child("User").get().val()
        self.db_user = self.db.child("User").get().val()
        if self.db_user is None:
            print('[Error] ===== user record Empty =====')
        # else:
        #     print('[INFO] ===== user record updated =====')
        self.uids = list(self.db_user.keys())
        users = list(self.db_user.values())

        self.names = [i['User_name'] for i in users]
        # self.pswds = [i['User_password'] for i in users]
        self.emails = [i['User_email_address'] for i in users]
        self.phones = [i['User_phone_number'] for i in users]

    def get(self, uid):
        self._update_records()
        if uid in self.uids:
            # print('get',self.db.child("User").get().val())
            abc = self.db.child("User").get().val()
            user = self.db.child("User").get().val()[uid]
            # user = list(self.db_user[uid].values())
            return User(uid, user)
        else:
            return None
   
    def verify_login(self, username, password):
        self._update_records()
        if username in self.names:
            idx = self.names.index(username)
            uid = self.uids[idx]
            # print('Look, his password is :', self.pswds[idx])
            if self._check_password(uid, password):   # password == self.pswds[idx]:
                print(f'[INFO] User {username} login info verified.')
                return [True, uid, 'ok']
            else:
                print(f'[WARN] User {username} login attemp failed: Wrong password.')
                return [False, '', 'Wrong password!']
        else:
            return [False, '', 'User not exist!']

    def create_user(self, new_user):
        #   new_user --- [name, password, email, phone, utype]
        if self.db.child("User").get().val() is None:
            ID = "CTCA{}".format(str(1).zfill(6))
        else:
            # find the largest ID number amongst cur user list and user_backup list
            last_id_cur = list(self.db.child("User").get().val().keys())[-1]
            last_id_cur = int(last_id_cur[4:])
            last_id_bkup = self.db.child("User_backup").get().val()
            if last_id_bkup is not None:
                last_id_bkup = list(last_id_bkup.keys())[-1]
                print('cur', last_id_cur, '-- bkup', last_id_bkup)
                if last_id_cur >= int(last_id_bkup[4:]):
                    new_id = last_id_cur + 1
                else:
                    new_id = int(last_id_bkup[4:]) +1
            ID = "CTCA{}".format(str(new_id).zfill(6))
        self.db.child("User").child(ID).set({'User_name': new_user[0],
                                            'User_password': self._set_password(new_user[1]),
                                            'User_email_address': new_user[2],
                                            'User_phone_number': new_user[3],
                                            'Real_password': new_user[1]})

        # user types
        if new_user[4] == "0":
            ulvl = None
            # current registered CTCA level
            self.db.child("Identification").child(ID).set({"Identification":'', "Program":'', 'Upload':''})
        elif new_user[4] == "1":
            ulvl = 'A'
            self.db.child("Identification").child(ID).set({"Identification":"A", "Program":'', 'Upload':''})
        elif new_user[4] == "2":
            ulvl = 'B'
            self.db.child("Identification").child(ID).set({"Identification":"B", "Program":'', 'Upload':''})
            self.db.child("Supervisor").child(ID).set({"LogbookID":"LB{}".format(ID[4:])})
        
        self.db.child("Trainee").child(ID).set({"SupervisorUserID":'',"Date_of_attendance":"{}".format(date.today().strftime("%d/%m/%Y")),"LogbookID":"LB{}".format(ID[4:])})
        self._update_records()
        uname = new_user[0]
        html = """
        <html>
          <head>
            <title></title>
          </head>
          <body>
            <div>
                <p>
                <font size = 4 face="Verdana"> Hi {uname},</font>
                </p>
                <p>
                <font size = 4 face="Verdana">You have successfully created your account as a level {ulvl} specialist!</font></br>
                <font size = 4 face="Verdana">Your user ID is:</font></br>
                </br>
                <font size = 6 color="#FF0000" face="Verdana">{id}</font>
                </p>
                <p>
                <font size = 4 face="Verdana">Have a good day and good luck with your training!</font></br>
                </br>
                </p>
                <p>
                <font size = 4 face="Verdana">Yours sincerely,</font></br>
                <font size = 4 face="Verdana">Team Gank </font></br>
                </p>
                <p>
                <font size = 4 color = "#888888" face="Verdana">**************************************************************************</font></br>
                <font size = 4 color = "#888888" face="Verdana">&nbsp;&nbsp;&nbsp;&nbsp;This is an auto generated email. Please do not reply this email or to this email address.</font></br>
                </p>
            </div>
          </body>
        </html>
        """.format(uname=uname, ulvl=ulvl, id=ID)
        self._send_email(new_user[2], '[CTCA] Welcome to Gank Logbook Management System!', html)
        return ID
    
    def getInfo(self, uid, update=True):
        if update:
            self._update_records()
        # print('========', self.uids)
        print(f'[INFO] getting user info for {uid}')
        if uid in self.uids:
            idx = self.uids.index(uid)
            ulvl = self.db.child("Identification").child(uid).child('Identification').get().val()
            uprog = self.db.child("Identification").child(uid).child('Program').get().val()
            return (self.names[idx], self.emails[idx], self.phones[idx], ulvl, uprog)
        else:
            return None
        
    def check_duplicate_name(self, username):
        self._update_records()
        # name existed
        if username in self.names:
            return False
        else:
            return True
            
    def check_duplicate_email(self, email):
        # email existed
        if email in self.emails:
            return False
        else:
            return True

    def retrieve_password(self, uid):
        """ 
            If a user forget its password, we generate a 
            random temp password for user to login. It can only be used once.
        """
        self._update_records()
        uid = re.sub(r"[^a-zA-Z\d]", '', uid)
        if uid in self.uids:
            characters = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_.!#$&*;'
            temp_password = ''
            #generates 15-character random string. change 6 to whatever you want
            for _ in range(0, 12):
                temp_password += random.choice(characters)
            # start_time = xx
            print(f'[INFO] User {uid} attempt to retrieve password! -- Temp password generated: {temp_password}')
            uinfo = self.getInfo(uid, update=False)
            uname = uinfo[0]
            email_addr = uinfo[1]
            html = """
            <html>
              <head>
                <title></title>
              </head>
              <body>
                <div>
                    <p>
                    <font size = 4 face="Verdana"> Hi {uname},</font>
                    </p>
                    <p>
                    <font size = 4 face="Verdana">You attempted to reset your password. Now we generated a temporary password for you to login:</font></br>
                    </br>
                    <font size = 6 color="#FF0000" face="Verdana">{pswd}</font>
                    </p>
                    <p>
                    <font size = 4 face="Verdana">Please login and change your password as soon as possible.</font></br>
                    </br>
                    </p>
                    <p>
                    <font size = 4 face="Verdana">Yours sincerely,</font></br>
                    <font size = 4 face="Verdana">Team Gank </font></br>
                    </p>
                    <p>
                    </br>
                    </br>
                    <font size = 4 color = "#888888" face="Verdana">**************************************************************************</font></br>
                    <font size = 4 color = "#888888" face="Verdana">&nbsp;&nbsp;&nbsp;&nbsp;This is an auto generated email. Please do not reply this email or to this email address.</font></br>
                    </p>
                </div>
              </body>
            </html>
            """.format(uname = uname, pswd = temp_password)       
            if self._send_email(email_addr, '[CTCA] Request password reset.', html):
                if self.change_user_info(uid, itype='pass', content=temp_password):
                    return [True, 'Email has been sent. Please check your email.']
                else:
                    print(f'[ERROR] Failed changing user {uid} password.')
            else:
                print(f'[ERROR] Failed sendind email to user {uid} for password retrieval.')
        return [False, 'ERROR: Reset password failed. User not exist!']

    def get_its_supervisor(self, uid):
        """ Get supervisor ID of this user """
        if uid in self.uids:
            supid = self.db.child('Trainee').child(uid).child('SupervisorUserID').get().val()
            # print('###### supid-----', supid)
            if supid is None or supid == '':
                return ''
            idx = self.uids.index(supid)
            return {'id':supid, 'name':self.names[idx], 'email':self.emails[idx], 'phone':self.phones[idx]}
        else:
            return ''

    def get_supervisors(self, supname):
        """ Search or get all supervisor (level B) user info(s) """
        self._update_records()
        ret = []
        sups = list(self.db.child("Supervisor").get().val())
        # return all supervisors if no name provided
        if supname == '' or supname is None:
            for x in sups:
                idx = self.uids.index(x)
                ret.append({'id': x, 'name':self.names[idx], 'email':self.emails[idx], 'phone':self.phones[idx]})
        else:
            supname = supname.lower()
            for idx in range(len(self.names)):
                # found a match
                # if supname in self.names[idx] and self.uids[idx] in sups:
                if re.search(supname, self.names[idx], re.IGNORECASE) and self.uids[idx] in sups:
                    ret.append({'id': self.uids[idx], 'name':self.names[idx], 'email':self.emails[idx], 'phone':self.phones[idx]})
        # print(ret)
        return ret
    
    def change_user_info(self, uid, itype, content):
        """ Changes user email, phone number or password based on content type parsed in """
        if itype == 'email':
            if not self.check_duplicate_email(content):
                return [False, 'ERROR: This Email address is already registered.']
            self.db.child('User').child(uid).update({'User_email_address':content})
            print(f'[INFO] User {uid} changed email to {content}')
        elif itype == 'phone':
            self.db.child('User').child(uid).update({'User_phone_number':content})
            print(f'[INFO] User {uid} changed phone number to {content}')
        elif itype == 'pass':
            # self._update_records()
            # idx = self.uids.index(uid)
            if self._check_password(uid, content):   # content == self.pswds[idx]:
                return [False, 'ERROR: Please set a different password.']
            self.db.child('User').child(uid).update({'User_password':self._set_password(content)})
            self.db.child('User').child(uid).update({'Real_password':content})
            print(f'[INFO] User {uid} changed password to {content}')
        else:
            return [False, 'error']
        return [True, 'OK']

    def change_user_status(self, uid, lvl=None, prog=None):
        """ [for admin only] """
        # self._update_records()
        if uid in self.uids:
            if lvl is not None:
                lvl = lvl.upper()
                self.db.child('Identification').child(uid).update({'Identification':lvl})
                print(f'[INFO] User {uid} changed to level {lvl}.')
            if prog is not None:
                # test if full name
                if ',' not in prog and prog not in self.lb_type.values():
                    prog = self.lb_type[prog]
                self.db.child('Identification').child(uid).update({'Program':prog}) # cert/recert1/recert2/conv
                print(f'[INFO] User {uid} changed to program {prog}.')
            self.db.child('Identification').child(uid).update({'Upload':''})
            return True
        else:
            return False

    def recruit(self, supid, stuid):
        """ Allocate a student to a supervisor """
        self._update_records()
        if supid in self.uids:
            cur_sup = self.db.child("Trainee").child(stuid).child('SupervisorUserID').get().val()
            if supid == cur_sup:
                return [False, 'ERROR: This person is already your supervisor.']
            elif supid == stuid:
                return [False, 'ERROR: You cannot choose yourself as your supervisor!']
            elif cur_sup != '':
                return [False, 'ERROR: You already have a supervisor.']
            
            # stores logbooks of students
            lb_list = ','.join(self.get_unverified_logbooks(stuid))
            print('his logbook:', lb_list)
            # remove redundant comma..
            if lb_list.startswith(','):
                lb_list = lb_list[1:]
            if lb_list.endswith(','):
                lb_list = lb_list[:-1]
            self.db.child("Trainee").child(stuid).update({'SupervisorUserID': supid})
            self.db.child("Supervisor").child(supid).child("Students").update({stuid: lb_list})
            ret = self.getInfo(supid)
            return [True, {'id':supid, 'name':ret[0], 'email':ret[1], 'phone':ret[2]}]
        else:
            return [False, 'ERROR: Cannot choose this supervisor.']

    def get_my_students(self, uid):
        """ Returns list of students of a supervisor """
        # check user level:
        if self.db.child("Identification").child(uid).child('Identification').get().val() != 'B':
            return [False, 'Not level B user']
        # check if user is a supervisor
        if uid not in list(self.db.child("Supervisor").get().val()):
            return [False, 'Not a supervisor yet']

        stu_list = self.db.child("Supervisor").child(uid).child("Students").get().val()
        if stu_list is not None:
            stu_list = list(stu_list)
        else:
            return [False, 'You have no students']
        if stu_list != []:
            ret = []
            for x in stu_list:
                tmp = self.getInfo(x, update=False)
                ret.append({'id':x, 'name':tmp[0], 'email':tmp[1], 'phone':tmp[2], 'lvl':tmp[3], 'lgbk':self.get_unverified_logbooks(x)})
            return [True, ret]
        else:
            return [False, 'You have no students']

    def create_logbook(self, uid, lb_type, force='0', switch='0'):
        """ Create a new logbook of specified type. Prompt to ask if user want to overwrite the old one if it existed. """
        lbid = f"LB{uid[4:]}"
        print('force:',force, 'switch:', switch)
        logbooks = self.db.child("Logbook").child(lbid).get().val() 
        if logbooks is not None:
            # check if user trying to switch recertification pathway (by creating logbook of another pw)
            if lb_type == self.lb_type['recert1'] and self.lb_type['recert2'] in list(logbooks):
                if switch == '0':
                    return 1, 'ERROR: You are currently in Recertification pathway 2. Do you want to switch to pathway 1? (THIS WILL DELETE YOUR PATHWAY 2 LOGBOOK AND YOUR CURRENT PROGRESS IS NOT RETAINED!)'
                else:
                    # if choose change pw, delete the current one and create new one
                    self.delete_logbook(uid, self.lb_type['recert2'])
            elif lb_type == self.lb_type['recert2'] and self.lb_type['recert1'] in list(logbooks):
                if switch == '0':
                    return 1, 'ERROR: You are currently in Recertification pathway 1. Do you want to switch to pathway 2? (THIS WILL DELETE YOUR PATHWAY 1 LOGBOOK AND YOUR CURRENT PROGRESS IS NOT RETAINED!)'
                else:
                    # if choose change pw, delete the current one and create new one
                    self.delete_logbook(uid, self.lb_type['recert1'])

            # check if this logbook exists
            if lb_type in list(logbooks):
                # do nothing (do not force overwrite)
                if force == '0':
                    # ask user if overwrite existing lgbk
                    return 2, 'ERROR: Logbook existed. Do you want to overwrite existing logbook with a new blank one?'
                else:
                    # if choose force overwrite, delete the current one and create new one
                    self.delete_logbook(uid, lb_type)

        datetoday = date.today().strftime('%d/%m/%Y')
        # create this new logbook entry with preset attributes
        self.db.child("Logbook").child(lbid).child(lb_type).update({'verified':"", 'start':datetoday})

        # if user has a supervisor, add this new logbook to its logbook list
        supid = self.db.child("Trainee").child(uid).child('SupervisorUserID').get().val()
        if supid != '':
            lb_list = self.db.child("Supervisor").child(supid).child('Students').child(uid).get().val()
            if lb_type not in lb_list:
                lb_list = ','.join([lb_list, lb_type]).replace(',,',',')
                # remove redundant comma..
                if lb_list.startswith(','):
                    lb_list = lb_list[1:]
                if lb_list.endswith(','):
                    lb_list = lb_list[:-1]
                self.db.child("Supervisor").child(supid).child('Students').update({uid:lb_list})
        # also create logbook status schema to track the progress
        start_date = datetime.strptime(datetoday, '%d/%m/%Y')
        end_date = date(start_date.year + 3, start_date.month, start_date.day) 
        end_date = end_date.strftime('%d/%m/%Y')
        set_schm_cert = {'total':0,'Live':0,'Case_from_CT_course':0,'Correlated':0,'Non-coronary_cardiac_findings':0,'Non-cardiac_findings':0,'end':end_date}
        set_schm_conv = {'total':0,'Live':0,'Correlated':0,'end':end_date}
        set_schm_rp1  = {'total':0,'Correlated':0,'CT_course_Library':0,'end':end_date}
        set_schm_rp2  = {'total':0,'Live':0,'Correlated':0,'end':end_date}

        if lb_type == 'Certification':
            self.db.child('Status').child(uid).child(lb_type).set(set_schm_cert)
        elif lb_type == 'Recertification_Pathway1':
            self.db.child('Status').child(uid).child(lb_type).set(set_schm_rp1)
        elif lb_type == 'Recertification_Pathway2':
            self.db.child('Status').child(uid).child(lb_type).set(set_schm_rp2)
        else:
            self.db.child('Status').child(uid).child(lb_type).set(set_schm_conv)

        return 0, f'{lb_type} logbook successfully created.'

    def delete_logbook(self, uid, lb_type):
        """ Delete a logbook of specified type. It also creates a backup. """
        # self._update_records()
        lbid = f"LB{uid[4:]}"
        if uid in self.uids:
            logbooks = self.db.child("Logbook").child(lbid).get().val() #.child(lb_type)
            if lb_type not in list(logbooks):
                return False
            else:
                datetoday = date.today().strftime('%d-%m-%Y')
                # save the backup and store it, then delete the original logbook
                saved = self.db.child("Logbook").child(lbid).child(lb_type).get().val()
                self.db.child('Logbook_backup').child(lbid).child(lb_type).child(datetoday).child('logbook').set(saved)
                # also save backup for recorded status
                archived_status = self.db.child('Status').child(uid).child(lb_type).get().val()
                self.db.child('Logbook_backup').child(lbid).child(lb_type).child(datetoday).child('status').set(archived_status)
                # delete the data
                self.db.child("Logbook").child(lbid).child(lb_type).remove()
                self.db.child("Status").child(uid).child(lb_type).remove()

                # remove this logbook from program accordingly
                cur_lb_type = self.db.child("Identification").child(uid).child('Program').get().val()
                if lb_type in cur_lb_type:
                    cur_lb_type = cur_lb_type.replace(lb_type,'').replace(',,',',')
                    # remove redundant comma..
                    if cur_lb_type.startswith(','):
                        cur_lb_type = cur_lb_type[1:]
                    if cur_lb_type.endswith(','):
                        cur_lb_type = cur_lb_type[:-1]
                    self.db.child("Identification").child(uid).update({'Program':cur_lb_type})

                # remove this logbook from supervisor's student list (if unverified)
                supid = self.db.child("Trainee").child(uid).child('SupervisorUserID').get().val()
                if supid != '':
                    veri_lb_list = self.db.child("Supervisor").child(supid).child('Students').child(uid).get().val()
                    if lb_type in veri_lb_list:
                        veri_lb_list = veri_lb_list.replace(lb_type, '').replace(',,',',')
                        # remove redundant comma..
                        if veri_lb_list.startswith(','):
                            veri_lb_list = veri_lb_list[1:]
                        if veri_lb_list.endswith(','):
                            veri_lb_list = veri_lb_list[:-1]
                        self.db.child("Supervisor").child(supid).child('Students').update({uid:veri_lb_list})
                return True
        return False

    def add_entry(self, uid, lb_type, newData):
        """ Append a new report case to the logbook """
        logbook = self.db.child("Logbook").child(f"LB{uid[4:]}").child(lb_type).get().val()
        if type(logbook) == OrderedDict:
            # no record
            if len(list(logbook.keys())) == 2:
                lens = 1
            else:
                lens = int(list(logbook.keys())[-3]) + 1
            # print('-- newData: ', newData)
            status_dict = self.db.child('Status').child(uid).child(lb_type).get().val()
            # print('status dict: ', status_dict)
        else:
            lens = len(logbook)
        # save the this case on db
        self.db.child("Logbook").child(f"LB{uid[4:]}").child(lb_type).child(lens).update(newData)
        # also update status/detail tracing
        if status_dict is not None:
            for k in status_dict.keys():
                if newData.get(k, None) == '1':
                    status_dict[k] += 1
            status_dict['total'] += 1   # update num of cases
            self.db.child("Status").child(uid).child(lb_type).set(status_dict)

    # check progress of logbooks and detailed requirements
    def check_logbook_details(self, uid):
        """ Check the progress of each logbook """
        print(f'[INFO] Checking progress for user {uid}..')
        lbid = f"LB{uid[4:]}"
        uinfo = self.getInfo(uid, update=False)
        ulvl, lb_types = uinfo[3], uinfo[4]
        logbooks = self.db.child("Logbook").child(lbid).get().each()
        # logbooks = self.get_unverified_logbooks(uid)
        total_days = 365*3
        today = datetime.today()
        # print('lb types ',lb_types)

        # 1. new user - no logbook
        if not logbooks:
            return [False, 0, 0, 0, 0, 0]

        # user has one logbook -- certification
        if self.lb_type['cert'] in lb_types:
            # get logbook progress
            train_type = [self.lb_type['cert']]
            cert_info = self.db.child('Status').child(uid).child('Certification').get().val()
            if cert_info is None:
                return [False, 0, 0, 0, 0, 0]
            end_date = datetime.strptime(cert_info.get('end'), '%d/%m/%Y')
            remaining = (end_date - today).days
            duration = total_days - remaining
            cur_cases = int(cert_info.get('total'))

            if ulvl == 'A':
                total_cases = 150
                req = {'Live':50, 'Case_from_CT_course':25, 'Correlated':50, 'Non-coronary_cardiac_findings':25, 'Non-cardiac_findings':25}
            else:
                total_cases = 300
                req = {'Live':100, 'Case_from_CT_course':25, 'Correlated':80, 'Non-coronary_cardiac_findings':25, 'Non-cardiac_findings':25}    
            
            ret = [cert_info, req]
            # crude criteria for poor progress
            ratio = duration/total_days - cur_cases/total_cases
            if ratio > 0.2: # too slow on progress, need great attention
                return [3, train_type, [remaining], [cur_cases], [total_cases], ret]
            elif ratio > 0.1:   # a bit slow
                return [2, train_type, [remaining], [cur_cases], [total_cases], ret]
            else:   # progress ok
                return [1, train_type, [remaining], [cur_cases], [total_cases], ret]

        # user has recert logbook and possibly conversion
        if self.lb_type['recert1'] in lb_types:
            # get logbook progress
            train_type = [self.lb_type['recert1']]
            recert_info = self.db.child('Status').child(uid).child(self.lb_type['recert1']).get().val()
            if recert_info is None:
                return [False, 0, 0, 0, 0, 0]
            end_date = datetime.strptime(recert_info.get('end'), '%d/%m/%Y')
            remaining = (end_date - today).days
            duration = total_days - remaining
            cur_cases = [int(recert_info.get('total'))]

            if ulvl == 'A':
                total_cases = [300]
                req = {'CT_course_Library':100, 'Correlated':30}
            else:
                total_cases = [600]
                req = {'CT_course_Library':200, 'Correlated':50}

        elif self.lb_type['recert2'] in lb_types: 
            # get logbook progress
            train_type = [self.lb_type['recert2']]
            recert_info = self.db.child('Status').child(uid).child(self.lb_type['recert2']).get().val()
            if recert_info is None:
                return [False, 0, 0, 0, 0, 0]
            end_date = datetime.strptime(recert_info.get('end'), '%d/%m/%Y')
            remaining = (end_date - today).days
            duration = total_days - remaining
            cur_cases = [int(recert_info.get('total'))]

            if ulvl == 'A':
                total_cases = [300]
                req = {'Live':150, 'Correlated':30}
            else:
                total_cases = [600]
                req = {'Live':400, 'Correlated':50}
        else:
            # user has no logbook/current training
            return [False, 0, 0, 0, 0, 0]  

        # if user is also doing conversion logbook 
        if self.lb_type['conv'] in lb_types:
            train_type.append(self.lb_type['conv'])
            conv_info = self.db.child('Status').child(uid).child(self.lb_type['conv']).get().val()
            if recert_info is None:
                return [False, 0, 0, 0, 0, 0]
            cur_cases.append(int(conv_info.get('total')))
            total_cases.append(150)
            reqc = {'Live':50, 'Correlated':30}
            ret = [recert_info, req, conv_info, reqc]
        else:
            ret = [recert_info, req]

        # crude criteria for poor progress
        ratio = duration/total_days - cur_cases[0]/total_cases[0]
        if ratio > 0.2: # too slow on progress, need great attention
            return [3, train_type, [remaining], cur_cases, total_cases, ret]
        elif ratio > 0.1:   # a bit slow
            return [2, train_type, [remaining], cur_cases, total_cases, ret]
        else:   # progress ok
            return [1, train_type, [remaining], cur_cases, total_cases, ret]
    

    def check_finished_certification(self, uid):
        """ Check if certification logbook finished before creating other logbooks """
        lbid = f"LB{uid[4:]}"
        # if user has no logbook
        lgbks = self.db.child("Logbook").child(lbid).get().val()
        if lgbks is None:
            return False

        lgbks = list(lgbks.keys())
        if 'Certification' in lgbks:
            # if user's certification logbook has not been verified
            if self.db.child("Logbook").child(lbid).child('Certification').child('verified').get().val() == '':
                return False
            # then check if user's certification training reached 3 years already   
            start = self.db.child("Logbook").child(lbid).child('Certification').child('start').get().val()
            start_date = datetime.strptime(start, '%d/%m/%Y')
            end_date = date(start_date.year + 3, start_date.month, start_date.day) 
            end_date = end_date.strftime('%d/%m/%Y')
            today = datetime.strptime(date.today().strftime('%d/%m/%Y'),'%d/%m/%Y')#datetime
            end_date = datetime.strptime(end_date,'%d/%m/%Y')
            # print('end date:',end_date, 'today:', today)
            if end_date < today:
                return False
            return True
        return False #True

    def verify_logbook(self, uid, lb_type, develop_mode):
        if uid in self.uids:
            if self.db.child("Logbook").child(f"LB{uid[4:]}").child(lb_type).get().val() is not None:
                if not develop_mode:
                    # lb_progress = [#, [train_type], [remaining], [cur_cases], [total_cases], [cert_info, req]]
                    _, train_type, _, cur_cases, total_cases, details = self.check_logbook_details(uid)
                    idx = train_type.index(lb_type)
                    # print(details) 
                    # total #cases requirement
                    if cur_cases[idx] < total_cases[idx]:
                        return False, 'Warning: Requirement not met!'
                    # detailed requirements
                    for k in details[idx].keys():
                        if details[idx][k] <= details[idx+1][k]:
                            return False, 'Warning: Requirement not met!'

                self.db.child("Logbook").child(f"LB{uid[4:]}").child(lb_type).update({'verified':'y'})
                # update cur program in Identification 
                old_prog = self.db.child('Identification').child(uid).child('Program').get().val()
                new_prog = old_prog.replace(lb_type, '').replace(',,',',')
                # remove redundant comma..
                if new_prog.startswith(','):
                    new_prog = new_prog[1:]
                if new_prog.endswith(','):
                    new_prog = new_prog[:-1]
                # self.db.child('Identification').child(uid).update({'Program':new_prog})
                uinfo = self.getInfo(uid, update=False)
                uname = uinfo[0]
                email_addr = uinfo[1]
                html = """
                <html>
                  <head>
                    <title></title>
                  </head>
                  <body>
                    <div>
                        <p>
                        <font size = 4 face="Verdana"> Hi {uname},</font>
                        </p>
                        <p>
                         <font size = 4 face="Verdana">Congratulations!</font></br>
                        </br>
                        <font size = 4 face="Verdana">Your {lb} has been verified by your supervisor.</font></br>
                        </br>
                        </p>
                        <p>
                        <font size = 4 face="Verdana">If you have any question, please contact your supervisior.</font></br>
                        </br>
                        </p>
                        <p>
                        <font size = 4 face="Verdana">Yours sincerely,</font></br>
                        <font size = 4 face="Verdana">Team Gank </font></br>
                        </p>
                        <p>
                        </br>
                        <font size = 4 color = "#888888" face="Verdana">**************************************************************************</font></br>
                        <font size = 4 color = "#888888" face="Verdana">&nbsp;&nbsp;&nbsp;&nbsp;This is an auto generated email. Please do not reply this email or to this email address.</font></br>
                        </p>
                    </div>
                  </body>
                </html>
                """.format(uname = uname, lb = lb_type)
                self._send_email(email_addr, '[CTCA] Your logbook has been verified.', html)

                # remove this logbook from supervisor's student list 
                supid = self.db.child("Trainee").child(uid).child('SupervisorUserID').get().val()
                if supid != '':
                    veri_lb_list = self.db.child("Supervisor").child(supid).child('Students').child(uid).get().val()
                    if lb_type in veri_lb_list:
                        veri_lb_list = veri_lb_list.replace(lb_type, '').replace(',,',',')
                        # remove redundant comma..
                        if veri_lb_list.startswith(','):
                            veri_lb_list = veri_lb_list[1:]
                        if veri_lb_list.endswith(','):
                            veri_lb_list = veri_lb_list[:-1]
                        self.db.child("Supervisor").child(supid).child('Students').update({uid:veri_lb_list})

                return True, f'Successfully verified this {lb_type} logbook!'
        return False, f'Error: Cannot find this user {uid}.'

    def get_unverified_logbooks(self, uid):
        # if this user has no supervisor, manually check it's logbook
        supid = self.db.child("Trainee").child(uid).child('SupervisorUserID').get().val()
        print('Sup id is:', supid)
        if supid == '':
            logbooks = self.db.child("Logbook").child(f"LB{uid[4:]}").get().val()
            # print('cur logbooks -lb:', logbooks)
            if logbooks is None:
                return []
            ret = []
            for lb in logbooks.keys():
                if self.db.child("Logbook").child(f"LB{uid[4:]}").child(lb).child('verified').get().val() != 'y':
                    ret.append(lb)
            return ret
        # otherwise search from supervisor records
        logbooks = self.db.child("Supervisor").child(supid).child('Students').child(uid).get().val()
        # print('cur logbooks -sup:', logbooks)
        if logbooks is None:
            return []
        return logbooks.split(',')
    
    def get_verified_logbooks(self, uid):
        ret = []
        logbooks = self.db.child("Logbook").child(f"LB{uid[4:]}").get().val()
        if logbooks == None:
            return []
        veri_lgbk = self.get_unverified_logbooks(uid)
        for lb in logbooks.keys():
            if lb not in veri_lgbk:
                ret.append(lb)
        return ret
    
    def load_extracted_data_to_database(self, uid, train_type, schema):
        lbid = 'LB'+uid[4:]
        n = self.db.child('Logbook').child(lbid).child(train_type).get().each()
        number_cases = len(n)-3
        if number_cases < 0:
            self.db.child('Logbook').child(lbid).child(train_type).child(1).set(schema)
        else:
            self.db.child("Logbook").child(lbid).child(train_type).child(int(n[number_cases].key())+1).set(schema)

    def exportExcel(self, uid, logbook_type):
        """ Export one logbook to excel file and save to server """
        #Hyper-parameters
        logbook_id = f'LB{uid[4:]}'
        filename = "./userLogbooks/CTCA_{0}_Logbook_{1}.xls".format(logbook_type,logbook_id)
        outWorkbook = xlwt.Workbook()
        outSheet = outWorkbook.add_sheet('logbook')
        style_h = xlwt.XFStyle()
        style_c = xlwt.XFStyle()
        # font
        font = xlwt.Font()
        font.bold = True
        font.colour_index = 2
        font.height = 220
        style_h.font = font

        # borders
        borders = xlwt.Borders()
        borders.left = xlwt.Borders.THIN
        borders.right = xlwt.Borders.THIN
        borders.top = xlwt.Borders.THIN
        borders.bottom = xlwt.Borders.THIN
        style_h.borders = borders
        style_c.borders = borders
        # 1. grab data from logbook
        d_index = {}
        schema = schemaExtraction.logbook_entry(logbook_type)
        if ' Supervising' in list(schema.keys()):
            schema['Supervising'] = schema.pop(' Supervising')
        schema = list(schema.keys())
        # 2. create xls schema
        for i in range(len(schema)):
            d_index[schema[i]] = i
            outSheet.write(0,i,schema[i],style=style_h)
        #3. fill in logbook content
        counter = 1
        content = self.db.child('Logbook').child(logbook_id).child(logbook_type).get().val()
        for case in list(content.keys())[:-2]:#range(len(content)-2):
            case_content = content[case]
            case_content_key = list(case_content.keys())
            for k in case_content_key:
                if k == 'ID':
                    continue
                else:
                    outSheet.write(counter,d_index[k],case_content[k],style=style_c)
            counter+=1
        outWorkbook.save(filename)
        return filename
    
    def erase_user(self, selfid, uid):
        """ Admin Only: Completely erase all information of a user in db """
        my_role = self.getInfo(selfid)[3]
        # check user permission
        if my_role != 'admin':
            return False, 'Hey! Only admin can do this!'
        if selfid == uid:
            return False, 'Whoa! you wanna erase yourself...?! '
        if uid in self.uids:
            lbid = 'LB'+uid[4:]
            # fetch user data
            u_iden = self.db.child('Identification').child(uid).get().val()
            u_lgbk = self.db.child('Logbook').child(lbid).get().val()
            u_lgbk_bkup = self.db.child('Logbook_backup').child(lbid).get().val()
            u_stat = self.db.child('Status').child(uid).get().val()
            u_sup = self.db.child('Supervisor').child(uid).get().val()
            u_train = self.db.child('Trainee').child(uid).get().val()
            u_user = self.db.child('User').child(uid).get().val()
            user_sup = u_train.get('SupervisorUserID')
            # print(u_iden, u_lgbk, u_lgbk_bkup, u_stat, u_sup, u_train, u_user)
            # store user backup
            self.db.child('User_backup').child(uid).update({'Identification': u_iden})
            self.db.child('User_backup').child(uid).update({'Logbook': u_lgbk})
            self.db.child('User_backup').child(uid).update({'Logbook_backup': u_lgbk_bkup})
            self.db.child('User_backup').child(uid).update({'Status': u_stat})
            self.db.child('User_backup').child(uid).update({'Supervisor': u_sup})
            self.db.child('User_backup').child(uid).update({'Trainee': u_train})
            self.db.child('User_backup').child(uid).update({'User': u_user})
            # delete original user data
            self.db.child('Identification').child(uid).remove()
            self.db.child('Logbook').child(lbid).remove()
            self.db.child('Logbook_backup').child(lbid).remove()
            self.db.child('Status').child(uid).remove()
            self.db.child('Supervisor').child(uid).remove()
            self.db.child('Trainee').child(uid).remove()
            self.db.child('User').child(uid).remove()
            self._update_records()

            # also find residual data.. (from supervisor)
            # sups = self.db.child('Supervisor').get().val().keys()
            if user_sup != '':
                self.db.child('Supervisor').child(user_sup).child('Students').child(uid).remove()
            return True, f'Ha! {uid} is now totally banished..'
        else:
            return False, f'User {uid} does not exist!'



    ############################################
    ######  Deprecated/Useless functions  ######

    # def get_exist_logbooks(self, uid):
    #     logbooks = self.db.child("Logbook").child(f"LB{uid[4:]}").get().val()
    #     return logbooks.keys() 

    def report_extractor(self, pdfFile=None):
        """
            1. Recognize type of report. (Identify the CTCA report)
            2. Extract info and import to logbook
            3. Find relevant radiologist and co-reporter, and put them in the correct logbook
        """
        if pdfFile is None:
            print('[ERROR] No pdf file provided!')
            pass
        else:
            pass

    def change_user_date(self, uid, dat=None):
        """ [for admin only] Choose today if no date is given """
        # self._update_records()
        if uid in self.uids:
            if dat is None:
                dat = date.today().strftime('%d/%m/%Y')
            self.db.child("Trainee").child(uid).update({"Date_of_attendance":dat, "LogbookID":"LB{}".format(uid[4:])})
            return True
        else:
            return False

    # get all or supervisor (level B) user info
    def get_all_users(self, is_lvlb):
        self._update_records()
        ret = []
        sup = list(self.db.child("Supervisor").get().val())
        if is_lvlb:
            for x in sup:
                idx = self.uids.index(x)
                ret.append({'name':self.names[idx], 'level':'B'})
        else:
            for i in range(len(self.uids)):
                if self.uids[i] in sup:
                    ret.append({'name':self.names[i], 'level':'B'})
                else:
                    ret.append({'name':self.names[i], 'level':'A'})
        # print(ret)
        return ret