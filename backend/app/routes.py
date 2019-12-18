#!/usr/bin/python
from flask import Flask, request, render_template, session, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import current_user, login_user, logout_user, login_required
from app import application, manager, bot_response
from app.extraction import nlpOperation, nlpModule, schemaExtraction
from collections import OrderedDict
import os, re, dialogflow, base64, io, xlwt
from datetime import date, datetime

####### Hyper-parameters #######
use_react = True
develop_mode = False
NAT = 'http://a161b893.ngrok.io'
####### Hyper-parameters #######

def myResponse(code, status, message=None, description=None, data=None):
    tmp = {"code": code, 
        "status": status,
    }
    if message:
        tmp["message"] = message
    if description:
        tmp["description"] = description
    if data:
        tmp["data"] = data

    resp = jsonify(tmp)
    resp.headers.add("Access-Control-Allow-Origin", "*")
    return resp

@application.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('mainpage'))
    return render_template('index.html')

@application.route('/login', methods=['GET', 'POST'])
def login():
    error_msg = None
    if current_user.is_authenticated:
        return redirect(url_for('mainpage'))

    if request.method == 'POST':
        if use_react:
            data = request.json
            username = data['User']
            password = data['Psw']
        else:
            username = request.form['u']
            password = request.form['p']

        # verify login info
        # msg: [ T/F, user_ID, error_message ]
        msg = manager.verify_login(username, password)
        error_msg = msg[2]
        # login successful
        if msg[0]:
            login_user(manager.get(msg[1]), remember = False)
            print("[INFO] Currently signed in:", current_user.name)

            if use_react:
                response_data = myResponse(200, "OK", "Login successful", "Login successful")
                return response_data, 200
            else:
                return redirect(url_for('mainpage'))
        # login failed
        else:
            # print(error_msg)
            if use_react:
                response_data = myResponse(400, "NOT OK", error_msg, "Enter again.")
                return response_data, 400
            else:
                flash(error_msg)
                return redirect(url_for('login'))

    elif not use_react and request.method == 'GET':
        return render_template('login.html')

@application.route('/register', methods=['GET', 'POST'])
def register_form():
    error_msg = None
    if request.method == 'POST':
        if use_react:
            data = request.json
            name = data['User']
            password = data['Psw']
            email = data['Email']
            phone = data['Phone']
            utype = data['Type']
        else:
            name = request.form['User_name']
            password = request.form['User_password']
            email = request.form['User_email_address']
            phone = request.form['User_phone_number']
            utype = request.form["Identification"]

        # check if this username is available
        if not manager.check_duplicate_name(name):
            error_msg = 'ERROR: Username already existed! Please choose another one.'
            if use_react:
                response_data = myResponse(400, "NOT OK", error_msg, "Enter again.")
                return response_data, 400
            else:
                flash(error_msg)
                return redirect(url_for('register_form'))
        # check if this email address is available
        elif not manager.check_duplicate_email(email):
            error_msg = 'ERROR: This Email address is already registered.'
            if use_react:
                response_data = myResponse(400, "NOT OK", error_msg, "Enter again.")
                return response_data, 400
            else:
                flash(error_msg)
                return redirect(url_for('register_form'))
        # legit new user info        
        else:
            # create table for new user
            new_id = manager.create_user([name, password, email, phone, utype])
            print(f'[INFO] New user {name}({new_id}) created.')
            msg = manager.verify_login(name, password)
            login_user(manager.get(msg[1]), remember = False)
            if use_react:
                response_data = myResponse(200, "OK", "user create", "redirect")
                return response_data, 200
            else:
                return redirect(url_for('mainpage'))

    elif not use_react and request.method == 'GET':
        return render_template('register.html')

@application.route('/mainpage.html')
@login_required
def mainpage():
    if not current_user.is_authenticated:
        print('[WARN] Not signed in yet!')
        return redirect(url_for('index'))
        
    if use_react:
        user = {'username': current_user.name}
        ulvl = manager.getInfo(current_user.id, update=False)[3]
        user['supervision'] = '-Logbook Supervision' if ulvl == 'B' else ''
        return render_template('mainpage.html', user=user)
    else:
        user = {'username': current_user.name}
        user['userid'] = current_user.id
        return render_template('main.html', user=user)

@application.route('/get_user_name', methods=['GET'])
@login_required
def get_user_name():
    if request.method == 'GET':
        info = manager.getInfo(current_user.id)
        response_data = myResponse(200, "OK", "ping success", "Get the userid and name.", {
            'name': current_user.name,
            'id': current_user.id,
            'email': info[1],
            'phone': info[2],
            'usertype': info[3],    # user level None/A/B
            # 'program': info[4],   # active user logbook type
        })
        return response_data, 200         

@application.route('/logout')
@login_required
def logout():
    print('[INFO] User %s logging out..' % current_user.name)
    logout_user()
    return redirect(url_for('index'))

# For admins - change a user's status
@application.route('/chstat/<uid>/<lvl>')
@application.route('/chstat/<uid>/<lvl>/<prog>')
@login_required
def change_status(uid, lvl=None, prog=None):
    if not current_user.is_authenticated:
        return 'login first, bro' 

    # verify admin to proceed
    mee = manager.getInfo(current_user.id)[3]
    if mee != 'admin':
        return f'Whoa stop! You are not allowed to do that! Lvl {mee} user'
    uid = 'CTCA'+uid
    if manager.getInfo(uid)[3] == 'admin':
        return "Hey! You can't just banish another admin.. "

    if manager.change_user_status(uid, lvl, prog):
        return f'OK: User {uid} changed to level {lvl} and program {prog}.'
    else:
        return f"Error: failed changing user {uid}'s status."

# change user's basic info
@application.route('/change_info', methods=['GET', 'POST'])
@login_required
def change_my_info():
    field = request.args.get('type')
    data = request.json

    ret = manager.change_user_info(current_user.id, field, data['data'])

    if ret[0]:
        response_data = myResponse(200, "OK", message=ret[1])
        return response_data, 200
    else:
        response_data = myResponse(400, "NOT OK", message=ret[1])
        return response_data, 400

# For admins - change a user's enrollment date
@application.route('/chdate/<uid>')
@application.route('/chdate/<uid>/<dat>')
@login_required
def change_date(uid, dat=None):
    # verify admin to proceed
    mee = manager.getInfo(current_user.id)[3]
    if mee != 'admin':
        return f'Whoa stop! You are not allowed to do that! Lvl {mee} user'
    uid = 'CTCA'+uid
    ##### temp use #####
    dat = manager.db.child("Trainee").child(uid).child("Date_of_attendance").get().val()
    ####################
    if manager.change_user_date(uid, dat):
        return f'OK: Set starting date to {dat} for user {uid}.'
    else:
        return f"Error: failed changing user {uid}'s starting date."

@application.route('/chpass/<uid>/<pswd>')
@login_required
def change_pswd(uid, pswd):
    # verify admin to proceed
    mee = manager.getInfo(current_user.id)[3]
    if mee != 'admin':
        return f'Whoa stop! You are not allowed to do that! Lvl {mee} user'
    uid = 'CTCA'+uid
    ret = manager.change_user_info(uid, 'pass', pswd)
    if ret[0]:
        return f'OK: Password of user {uid} is set to {pswd}'
    else:
        return f"Error: failed changing user {uid}'s password. {ret[1]}"
    
# self-register to a supervisor
@application.route('/recruit', methods=['POST'])
@login_required
def register_supervisor():
    uid = current_user.id
    supid = request.args.get('supid')
    supinfo = manager.recruit(supid, uid)
    if supinfo[0]:
        return myResponse(200, "OK", message='Success', data=supinfo[1]), 200
    else:
        return myResponse(400, "BAD", message=supinfo[1]), 400   

# manually allocate students to supervisor
@application.route('/recruit/<stuid>')
@application.route('/recruit/<supid>/<stuid>')
@login_required
def recruit_students(stuid, supid=None):
    mee = manager.getInfo(current_user.id)[3]
    if supid is None:
        # for supervisors choosing students
        if mee != 'B':
            return f'No way! You are not even a supervisor! Lvl {mee} user'
        supid = current_user.id
    else:
        # for admin allocating student to supervisor
        if mee != 'admin':
            return f'Stop it! Only admin can choose two sides! Lvl {mee} user'
        supid = 'CTCA'+supid

    stuid = 'CTCA'+stuid
    if manager.recruit(supid, stuid)[0]:
        return f'OK: Student {stuid} is now enslaved by supervisor {supid}.'
    else:
        return f'ERROR: Supervisor {supid} failed recruiting student {stuid}.'


@application.route('/get_students', methods=['GET', 'POST'])
@login_required
def get_students():
    ret = manager.get_my_students(current_user.id)
    if ret[0]:
        return myResponse(200, "OK", message='Success', data=ret[1]), 200
    else:
        return myResponse(400, "BAD", message=ret[1]), 400

@application.route('/verify_logbook', methods=['GET', 'POST'])
@login_required
def verify_logbook():
    stuid = request.args.get('uid')
    lb_type = request.args.get('lb_type')
    error_msg = ''

    mee = manager.getInfo(current_user.id, update=False)[3]
    if mee != 'B' and mee != 'admin':
        error_msg =  f'No way! You are not even a supervisor! Lvl {mee} user'
    # uid = 'CTCA'+uid
    # lb_type = manager.lb_type[lb_type]
    ret, error_msg = manager.verify_logbook(stuid, lb_type, develop_mode)
    if ret:
        return myResponse(200, "OK", message=error_msg), 200
    else:
        return myResponse(400, "BAD", message=error_msg), 400

# # quickly check user type (need change permission)
# @application.route('/utype/<uid>')
# def test_usertypes(uid):
#     ret = manager.getInfo('CTCA'+uid)
#     if ret:
#         return 'Level ' + ret[3] + ' - ' + ret[4]
#     else:
#         return 'Found no such person.'

# # check current training progress
# @application.route('/chk')
# @application.route('/chk/<uid>')
# @login_required
# def chk_progress(uid=None):
#     if uid is None:
#         uid = current_user.id
#     else:
#         uid = 'CTCA'+uid
#     prog = manager.check_progression(uid)
#     ret = f'Total {prog[2]} days - {prog[3]} out of {prog[4]} cases completed. {365*3-int(prog[2])} days left.'
#     details = manager.check_logbook_details(uid)
#     finished = manager.get_verified_logbooks(uid)

#     if prog[0] == 1:
#         return 'Progress OK: ' + ret +f' {details[0]},{details[1]} -- finished: {finished}.'
#     elif prog[0] == 2:
#         return 'Progress a bit slow: ' + ret
#     else:    
#         return 'Progress too bad! ' + ret
# Retrieve user password
@application.route('/forget_password', methods=['GET', 'POST'])
def forget_password(uid=None):
    uid = request.json['uid']
    ret = manager.retrieve_password(uid)
    if ret[0]:
        response_data = myResponse(200, "OK", message=ret[1])
    else:    
        response_data = myResponse(400, "bad", message=ret[1])
    return response_data, 200

# Deprecated/Useless route
@application.route('/get_users/<lvlb>', methods=['GET', 'POST'])
@login_required
def get_users(lvlb):
    # lvlb = request.args.get('lvlb')
    if lvlb == 'b':
        response_data = myResponse(200, "OK", message=manager.get_all_users(True))
    else:    
        response_data = myResponse(200, "OK", message=manager.get_all_users(False))
    return response_data, 200

@application.route('/erase/<uid>')
@application.route('/erase/<uid>/<yes>')
@login_required
def erase_user(uid=None, yes=False):
    my_role = manager.getInfo(current_user.id)[3]
    if my_role != 'admin':
        return 'Hey! Only admin can do this!'
    print(f'[WARNING] Admin is tring to erase user {uid}! Take a look!')
    if yes:
        ret, error_msg = manager.erase_user(current_user.id, uid)
        return error_msg
    else:
        return f'Dear admin, are you sure you wanna erase user {uid}??'

# search for or get all supervisors
@application.route('/get_supervisors', methods=['GET', 'POST'])
@login_required
def get_supervisors():
    name = request.args.get('name')
    response_data = myResponse(200, "OK", message=manager.get_supervisors(name))
    return response_data, 200 

@application.route('/get_its_supervisor', methods=['GET', 'POST'])
@login_required
def get_its_supervisor():
    uid = current_user.id
    response_data = myResponse(200, "OK", message=manager.get_its_supervisor(uid))
    return response_data, 200       

# get user's current progress on every logbooks, including finished ones.
@application.route('/get_progress', methods=['GET', 'POST'])
@login_required
def get_progress():
    # prog = manager.check_progression(current_user.id)   # [comment, train_type, cur_duration, cur_cases, total_cases]
    prog = manager.check_logbook_details(current_user.id)    # [comment, train_type, cur_duration, cur_cases, total_cases, [lgbk_prog, req]]
    finished = manager.get_verified_logbooks(current_user.id)
    print(finished)
    if isinstance(prog[2], list):
        remaining = [str(prog[2][0])+' day(s)', 'N/A']
    else:
        remaining = [str(prog[2])+' day(s)']

    # print(prog)
    if prog[0]:
        response_data = jsonify({
            "code": 200,
            "status": "success",
            "comment": prog[0],     # comment on user progress (ok or slow)
            "type": prog[1],        # user logbook type
            "duration": prog[2],    # days after user started this training
            "remain": remaining,    # days left
            "cases": prog[3],       # cases done
            "total": prog[4],       # total num of cases
            "details": prog[5],     # detailed requirements
            "finished": finished,   # finished logbooks/trainings
        })
        print('My response:', response_data)
        response_data.headers.add("Access-Control-Allow-Origin", "*")
        return response_data, 200
    else:
        response_data = jsonify({
            "code": 400,
            "status": "success",
            "comment": [],     # comment on user progress (ok or slow)
            "type": [],        # user logbook type
            "duration": [],    # days after user started this training
            "remain": [],      # days left
            "cases": [],       # cases done
            "total": [],       # total num of cases
            "details": [],     # detailed requirements
            "finished": [],    # finished logbooks/trainings
        })
        response_data.headers.add("Access-Control-Allow-Origin", "*")
        return response_data, 400

@application.route('/get_logbook', methods=['GET', 'POST'])
@login_required
def get_logbook():
    # Catch the page and per_page from fronted by using url's args.
    per_page = int(request.args.get('per_page'))
    page = int(request.args.get('page'))
    # Catch the data that sned from fronted.
    data = request.json
    # Load the data from firebase depend on the ID.              2 lb types ????????????
    if 'id' in data.keys():
        uid = data['id']
    else:
        uid = current_user.id
    # lb_type = manager.getInfo(uid)[4]
    lb_type = request.args.get('lb_type')
    # logbook = manager.db.child("Logbook").child(f"LB{uid[4:]}").child(lb_type).get()

    # print('I get logbook: ',manager.db.child("Logbook").child(f"LB{uid[4:]}").child(lb_type).get().val())
    logbook = manager.db.child("Logbook").child(f"LB{uid[4:]}").child(lb_type).get()
    # Create a copy of data and add the id columns into each dict.
    if type(logbook.val()) == OrderedDict:
        a = []
        for i in logbook.val():
            if i == 'verified':
                continue
            if i == 'start':
                continue
            else:
                logbook.val()[i]['ID'] = int(i)
                a.append(logbook.val()[i])
    else:
        if logbook.val() == None:
            a = []
        else:
            a = logbook.val()
            for i,j in enumerate(a):
                if j == None:
                    continue
                else:
                    j['ID'] = i
            while None in a:
                a.remove(None)

    # If there is a search request, we need to filter the data first.
    # I will create a copy of data first as well.
    filter_a = []
    if data['query'] != '':
        for i in a:
            for j in i.values():
                if str(data['query']) in str(j):
                    filter_a.append(i)
                    break
    else:
        filter_a = a
    
    # Now, use the data after filtering to calculate the total page, and total number of data.
    total_page = len(filter_a) // int(per_page) + 1
    total = len(filter_a)
    if page == total_page:
        filter_a = filter_a[(page - 1) * per_page:]
    else:
        filter_a = filter_a[(page - 1) * per_page:(page - 1) * per_page + per_page]
    # Set up for the response data.
    response_data = jsonify({
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_page": total_page,
        "data": filter_a
    })
    response_data.headers.add("Access-Control-Allow-Origin", "*")
    
    # Same as: Response(json.dumps(response_data), mimetype='application/json'), 200
    return response_data, 200

@application.route('/rowadd', methods=['GET', 'POST'])
@login_required
def rowadd():
    # Get the data send from frontend.
    data = request.json
    # Insert new data into firebase.
    # lb_type = manager.getInfo(current_user.id)[4]
    lb_type = request.args.get('lb_type')
    manager.add_entry(current_user.id, lb_type, data['newData'])
    # Response ok to forntend.
    response_data = myResponse(200, 'OK')
    return response_data, 200

@application.route('/rowupdate', methods=['GET', 'POST'])
@login_required
def rowupdate():
    # Get the data send from frontend.
    data = request.json
    # Update the correspond row with new data.
    # lb_type = manager.getInfo(current_user.id)[4]
    lb_type = request.args.get('lb_type')
    uid = current_user.id
    case_id = data.get('newData').get('ID')
    newData = data.get('newData')
    newData.pop('ID')
    manager.db.child("Logbook").child(f"LB{uid[4:]}").child(lb_type).child(case_id).update(newData)
    
    # also update status/detail tracing
    status_dict = manager.db.child('Status').child(uid).child(lb_type).get().val()
    for k in status_dict.keys():
        if data['newData'].get(k, None) == '1':
            status_dict[k] += 1
    manager.db.child("Status").child(uid).child(lb_type).set(status_dict)

    # Response ok to forntend.
    response_data = myResponse(200, 'OK')
    return response_data, 200

@application.route('/rowdelete', methods=['GET', 'POST'])
@login_required
def rowdelete():
    # Get the data send from frontend.
    data = request.json
    # Remove the data in firebase with correspond id.
    # lb_type = manager.getInfo(current_user.id)[4]
    lb_type = request.args.get('lb_type')
    uid = current_user.id
    case_id = data['oldData']['ID']
    tmp = manager.db.child("Logbook").child(f"LB{uid[4:]}").child(lb_type).child(case_id).get().val()
    manager.db.child("Logbook").child(f"LB{uid[4:]}").child(lb_type).child(case_id).remove()
    
    # also update status/detail tracing
    status_dict = manager.db.child('Status').child(uid).child(lb_type).get().val()
    for k in status_dict.keys():
        if tmp.get(k, None) == '1':
            status_dict[k] -= 1
    status_dict['total'] -= 1   # update num of cases
    manager.db.child("Status").child(uid).child(lb_type).set(status_dict)

    # Response ok to forntend.
    response_data = myResponse(200, 'OK')
    return response_data, 200
    
# get current public ip address and send to frontend for downloading
@application.route('/get_url', methods=['GET', 'POST'])
def get_url():
    le_url = NAT + "/downloadExcel/CTCA_"
    response_data = myResponse(200, "OK", message=le_url)
    return response_data, 200

# read user uploaded pdf, then extract data an load into db
@application.route('/extract_pdf', methods=['GET', 'POST'])
@login_required
def extract_pdf():
    train_type = request.args.get('train_type')
    uname = current_user.name
    uid = current_user.id
    lbid = 'LB'+uid[4:]
    # do NLP on uploaded pdf
    f = request.files['filepond']
    f = io.BytesIO(f.read())
    data = nlpOperation.document(f)
    manager.db.child('Identification').child(current_user.id).update({'Upload':train_type})

    cor,car,native,aorta = '0','0','0','0'
    if 'Coronary' in data or 'coronary' in data:
        native = '1'
    for j in data.split('\n'):
        if re.findall(r"[Aa][Dd][Dd][Ii][Tt][Ii][Oo][Nn][Aa][Ll].*[Cc][Aa][Rr][Dd][Ii][Aa][Cc].*[Ff][Ii][Nn][Dd][Ii][Nn][Gg][Ss]",j):
            cor, car = '1', '1'
            break
    sclass = nlpOperation.main_processing(f,sample = True)
    target_date,tartget_fac,dlp_value,id_value,target_Dr = sclass.execute()
    aorta = '1' if native == '0' else '0'
    target_date = target_date[0] if len(target_date)>0 else ""
    co_reps = target_Dr['Co-report']
    co_reps = co_reps.remove(uname) if uname in co_reps else co_reps
    co_rep = ','.join(co_reps)
    sup = ','.join(target_Dr['Supervisor'])
    # make sure consistent date format
    try:
        target_date = datetime.strptime(target_date, '%d-%b-%Y')
        target_date = target_date.strftime('%d/%m/%Y')
    except:
        pass

    # put extracted info into database
    if '_' in train_type:
        recertf = train_type.split('_')[0]
        pathway = train_type.split('_')[1][-1]
        schema = schemaExtraction.logbook_entry("Recertification",path_way = pathway)
        train_type = recertf.capitalize() +'_Pathway'+str(pathway)
    else:
        schema = schemaExtraction.logbook_entry(train_type)
    if ' Supervising' in schema.keys():
        schema['Supervising'] = schema.pop(' Supervising')
    keys = ['Date','Facility','DLP','UEN_OR_Patient_ID','Native_Coronary','Graft_Or_Thoracic_Aorta','Non-coronary_cardiac_findings','Non-cardiac_findings','Reporting_Doctor','Co_reporting','Supervising']
    values = [target_date,tartget_fac,dlp_value,id_value,native,aorta,cor,car,co_rep,co_rep,sup]
    for k,v in zip(keys,values):
        if k in schema:
            schema[k] = v
    # manager.load_extracted_data_to_database(uid, train_type, schema)

    n = manager.db.child('Logbook').child(lbid).child(train_type).get().each()
    number_cases = len(n)-3
    # print('we have ',number_cases)
    if number_cases < 0:
        manager.db.child('Logbook').child(lbid).child(train_type).child(1).set(schema)
    else:
        # print('now you have ', schema)
        manager.db.child("Logbook").child(lbid).child(train_type).child(int(n[number_cases].key())+1).set(schema)

    # print('- 1 UPDATED DONE-')
    # also update status/detail tracing
    status_dict = manager.db.child('Status').child(uid).child(train_type).get().val()
    for k in status_dict.keys():
        if schema.get(k, None) == '1':
            status_dict[k] += 1
    status_dict['total'] += 1   # update num of cases
    manager.db.child("Status").child(uid).child(train_type).set(status_dict)

    # notify the user if there are unextracted fields
    if '' in schema.values():
        response_data = myResponse(400, "bad", message='Unfortunately, there are data unextracted from this report. Please manually edit them.')
        return response_data, 200
    else:
        response_data = myResponse(200, "ok", message='Case successfully added')
        return response_data, 200

@application.route('/check_logbook_exist', methods=['GET', 'POST'])
@login_required
def check_logbook_exist():
    ret = manager.get_unverified_logbooks(current_user.id)
    print(ret)
    response_data = myResponse(200, "success", data=ret)
    return response_data, 200

@application.route('/create_logbook', methods=['GET', 'POST'])
@login_required
def create_logbook():
    error_msg = ''
    lb_type = request.args.get('lb_type')
    is_force = request.args.get('force')    # '1': force to create new lgbk
    is_switch = request.args.get('switch')  # '1': switch to new lgbk pathway
    ulvl = manager.getInfo(current_user.id)[3]

    if not develop_mode:
        # limit what logbooks can user create
        if ulvl == 'A' and lb_type != 'Certification':
            allowed = manager.check_finished_certification(current_user.id)
            if not allowed:
                error_msg = 'ERROR: Requirement not met. Have you passed your Certification training?'
                # print(error_msg)
                response_data = myResponse(400, "bad", error_msg)
                return response_data, 400
        elif ulvl == 'B' and (lb_type == 'Certification' or lb_type == 'Conversion'):
            error_msg = f'ERROR: Level B user cannot create new {lb_type} logbooks.'
            response_data = myResponse(400, "bad", error_msg)
            return response_data, 400

    ret, error_msg = manager.create_logbook(current_user.id, lb_type, is_force, is_switch)
    # conflict in creating recertification logbook pathways
    if ret == 1:
        # print(error_msg)
        response_data = myResponse(400, "swch", error_msg)
        return response_data, 400
    # creating a logbook that already exist    
    elif ret == 2:
        # print(error_msg)
        response_data = myResponse(400, "dup", error_msg)
        return response_data, 400
    
    # set/update user's on-going training/logbook
    cur_lb_type = manager.getInfo(current_user.id)[4]
    # 1. start new conversion
    if lb_type == manager.lb_type['conv']:
        if lb_type not in cur_lb_type:
            manager.change_user_status(current_user.id, prog=cur_lb_type+','+lb_type)
    # 2. add new logbook into cur training string
    elif manager.lb_type['conv'] in cur_lb_type:
        if lb_type not in cur_lb_type:
            manager.change_user_status(current_user.id, prog=lb_type+','+cur_lb_type)
    # 3. change to new logbook type
    else:
        manager.change_user_status(current_user.id, prog=lb_type)

    response_data = myResponse(200, "OK", error_msg)
    return response_data, 200

@application.route('/logbook_exist', methods=['GET', 'POST'])
@login_required
def logbook_exist():
    ret = manager.get_unverified_logbooks(current_user.id)
    print(ret)
    response_data = myResponse(200, "success", data={'logbook':ret})
    return response_data, 200

@application.route('/remove_logbook', methods=['GET', 'POST'])
@login_required
def remove_logbook():
    lb_type = request.args.get('lb_type')
    ret = manager.delete_logbook(current_user.id, lb_type)
    
    if ret:
        response_data = myResponse(200, "success")
        return response_data, 200
    else:
        response_data = myResponse(400, "not exist")
        return response_data, 400

@application.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True)
    para = data.get('queryResult').get('parameters')
    session = data.get('session')
    uinfor = session.split('/')[-1].split('_')
    student_name = uinfor[0]
    sid = uinfor[1]
    srole = uinfor[2]
    Bot = bot_response.botResponse(student_name,sid,srole,NAT)
    return Bot.responses()

def detect_intent_texts(project_id, session_id, text, language_code):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    if text:
        text_input = dialogflow.types.TextInput(
            text=text, language_code=language_code)
        query_input = dialogflow.types.QueryInput(text=text_input)
        response = session_client.detect_intent(
            session=session, query_input=query_input)
        print('response is ',response)
        return response.query_result.fulfillment_text

@application.route('/send_message', methods=['POST'])
def send_message():
    message = request.form['message']
    print('message is ',message)
    project_id = os.getenv('DIALOGFLOW_PROJECT_ID')

    pdf_par = re.compile(r'PDF_PAR_*')
    uname = current_user.name
    uid = current_user.id
    urole = manager.getInfo(uid)[3]
    print('========loged in user is ',uname,uid,urole)
    
    fulfillment_text = detect_intent_texts(project_id, uname+'_'+uid+'_'+urole, message, 'en')
    response_text = { "message":  fulfillment_text }
    return jsonify(response_text)

# run Flask app
@application.route('/send_file', methods=['POST'])
def send_file():
    #1.obtain current user infor
    project_id = os.getenv('DIALOGFLOW_PROJECT_ID')
    uname = current_user.name
    uid = current_user.id
    urole = manager.getInfo(uid)[3]
    match = re.search("\d{6}", uid)
    logbook_id = 'LB'+match[0]
    print('loged in user is ',uname,uid,urole)
    #2. do NLP on uploaded pdf
    message = request.form['message']
    filename = request.form['fileName']

    data = base64.b64decode(message)
    file = io.BytesIO(data)
    pp = nlpOperation.document(file)
    cor,car,native,aorta = '0','0','0','0'
    if 'Coronary' in pp or 'coronary' in pp:
        native = '1'
    for j in pp.split('\n'):
        if re.findall(r"[Aa][Dd][Dd][Ii][Tt][Ii][Oo][Nn][Aa][Ll].*[Cc][Aa][Rr][Dd][Ii][Aa][Cc].*[Ff][Ii][Nn][Dd][Ii][Nn][Gg][Ss]",j):
            cor,car = '1','1'
            break
    # target_date,tartget_fac,dlp_value,id_value,target_Dr = step_2._get_information(pp)
    sclass = nlpOperation.main_processing(file,sample = True)
    target_date,tartget_fac,dlp_value,id_value,target_Dr = sclass.execute()
    aorta = '1' if native == '0' else '0'
    target_date = target_date[0] if len(target_date)>0 else ""
    co_reps = target_Dr['Co-report']
    co_reps = co_reps.remove(uname) if uname in co_reps else co_reps
    co_rep = ','.join(co_reps)
    sup = ','.join(target_Dr['Supervisor'])
    #convert date format:
    try:
        target_date = datetime.strptime(target_date, '%d-%b-%Y')
        target_date = target_date.strftime('%d/%m/%Y')
    except:
        pass

    #3. put extracted info into database
    train_type = manager.db.child('Identification').child(uid).child('Upload').get().val()
    if '_' in train_type:
        recertf = train_type.split('_')[0]
        pathway = train_type.split('_')[1][-1]
        schema = schemaExtraction.logbook_entry("Recertification",path_way = pathway)
        train_type = recertf.capitalize() +'_Pathway'+str(pathway)
    else:
        schema = schemaExtraction.logbook_entry(train_type)
    if ' Supervising' in schema.keys():
        schema['Supervising'] = schema.pop(' Supervising')
    keys = ['Date','Facility','DLP','UEN_OR_Patient_ID','Native_Coronary','Graft_Or_Thoracic_Aorta','Non-coronary_cardiac_findings','Non-cardiac_findings','Reporting_Doctor','Co_reporting','Supervising']
    values = [target_date,tartget_fac,dlp_value,id_value,native,aorta,cor,car,co_rep,co_rep,sup]
    for k,v in zip(keys,values):
        if k in schema:
            schema[k] = v
    n = manager.db.child('Logbook').child(logbook_id).child(train_type).get().each()
    number_cases = len(n)-3
    if number_cases < 0:
        manager.db.child('Logbook').child(logbook_id).child(train_type).child(1).set(schema)
    else:
        manager.db.child("Logbook").child(logbook_id).child(train_type).child(int(n[number_cases].key())+1).set(schema)

    #update status
    total = manager.db.child('Status').child(uid).child(train_type).child('total').get().val()
    manager.db.child('Status').child(uid).child(train_type).child('total').set(total+1)
    if train_type == 'Certification':
        cardiac_findings = manager.db.child('Status').child(uid).child(train_type).child('Non-cardiac_findings').get().val()
        coronary_cardiac_findings = manager.db.child('Status').child(uid).child(train_type).child('Non-coronary_cardiac_findings').get().val()
        manager.db.child('Status').child(uid).child(train_type).child('Non-cardiac_findings').set(cardiac_findings+int(car))
        manager.db.child('Status').child(uid).child(train_type).child('Non-coronary_cardiac_findings').set(coronary_cardiac_findings+int(cor))

    message = 'Upload_File_Analysis+' + filename
    fulfillment_text = detect_intent_texts(project_id, uname+'_'+uid+'_'+urole, message, 'en')
    response_text = { "message":  fulfillment_text }
    return jsonify(response_text)


@application.route('/extractExcel', methods=['GET', 'POST'])
def extract_excel():
    uid = request.args.get('uid')
    lb_type = request.args.get('lb_type')
    fname = manager.exportExcel(uid, lb_type)
    # link = "<a href='http://e2f2697a.ngrok.io/downloadExcel/{0}' download={1}>{2}</a>".format(fname,fname,fname)
    response_data = myResponse(200, "OK", fname)
    return response_data, 200

@application.route('/downloadExcel', methods=['GET', 'POST'])
@application.route('/downloadExcel/<fname>', methods=['GET', 'POST'])
@login_required
def download(fname=None): 
    if fname is None:
        uid = request.args.get('uid')
        lb_type = request.args.get('lb_type')
        fname = manager.exportExcel(uid, lb_type)
        # link = "< a href=' ' download={1}>{2}</ a>".format(fname,fname,fname)

    print('DOWNLOAD?>>>>>>>>>>>>>',os.getcwd())
    return send_from_directory(directory=os.getcwd()+'/userLogbooks', filename=fname)






