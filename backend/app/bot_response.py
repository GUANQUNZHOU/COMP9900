from flask import request,jsonify,make_response
import os,pyrebase,re,xlwt,json
from datetime import date,datetime
from app.extraction import schemaExtraction,nlpOperation, nlpModule
from app import manager
import dialogflow_v2 as dialogflow
 
class botResponse():
    '''
    Class used for generating chatbot responses
    Input: 1. user name; 2. user ID; 3. User role(A or B)
    Output: Dictionary: result["fulfillmentText"] = some responeses
    '''
    def __init__(self,name, ids, role, NAT):
        self.name = name
        self.ids = ids
        self.role  = role
        self.result = {}
        self.req = request.get_json(force=True)
        self.para = self.req.get('queryResult').get('parameters')
        match = re.search("\d{6}", self.ids)
        self.logbook_id = 'LB'+match[0]
        self.action = self.req.get('queryResult').get('action')
        self.reportname = ''
        self.Training_Types = self.para.get("Training_Types")
        self.Training_Types_Re = self.para.get("Training_Types_Re")
        self.NAT = NAT


    def log_create(self,logbook_type,pathway=False):
        '''
        Functon used for creating logbooks
        Input: Logbook Type
        Process: Creat new logbooks in Tables:
            1.Logbook 2.Status 3.Identification.ID.Program 4.Supervisor.SupID.students.ID
        '''
        manager.db.child("Logbook").child(self.logbook_id).child(logbook_type).child("verified").set("")
        manager.db.child("Logbook").child(self.logbook_id).child(logbook_type).child("start").set(date.today().strftime('%d/%m/%Y'))
        #1. obtain logbook creation and estimated end time
        start = date.today().strftime('%d/%m/%Y')
        start_date = datetime.strptime(start, '%d/%m/%Y')
        end_date = date(start_date.year + 3, start_date.month, start_date.day) 
        end_date = end_date.strftime('%d/%m/%Y')
        #2. geberate status table
        set_schm_certify = {'total':0,'Live':0,'Case_from_CT_course':0,'Correlated':0,'Non-coronary_cardiac_findings':0,'Non-cardiac_findings':0,'end':end_date}
        set_schm_conv = {'total':0,'Live':0,'Correlated':0,'end':end_date}
        set_schm_rp1 = {'total':0,'Correlated':0,'CT_course_Library':0,'end':end_date}
        set_schm_rp2 = {'total':0,'Live':0,'Correlated':0,'end':end_date}
        if logbook_type == 'Certification':
            manager.db.child('Status').child(self.ids).child('Certification').set(set_schm_certify)
        elif logbook_type == 'Recertification_Pathway1':
            manager.db.child('Status').child(self.ids).child('Recertification_Pathway1').set(set_schm_rp1)
        elif logbook_type == 'Recertification_Pathway2':
            manager.db.child('Status').child(self.ids).child('Recertification_Pathway2').set(set_schm_rp2)
        else:
            manager.db.child('Status').child(self.ids).child('Conversion').set(set_schm_conv)
        #3. update identification and supervisor table
        manager.db.child('Identification').child(self.ids).child('Program').set(logbook_type)
        supID = manager.db.child('Trainee').child(self.ids).child('SupervisorUserID').get().val()
        if supID:
            currentStudlog = manager.db.child('Supervisor').child(supID).child('Students').child(self.ids).get().val()

            if not currentStudlog:
                manager.db.child('Supervisor').child(supID).child('Students').child(self.ids).set(logbook_type)
            else:
                manager.db.child('Supervisor').child(supID).child('Students').child(self.ids).set(logbook_type+', '+currentStudlog)
        print('created type is ',logbook_type)

    def log_type_return(self,overwrite=False):
        '''
        Functon that defines rules for creating logbooks and overwrting logbooks
        Input: Parameter contains logbook type
        Rules:
            1. no logbooks -> Certification
            2. 1 logbook -> Certification [Overwrite]
                         -> Recertification/Conversion -> check training time >= 3year and verified = 'y'
            3. >=2 logbooks [only allow for Recertification/Conversion]
            4. If overwrite => update tables:
                1.Logbook 2.Status 3.Identification.ID.Program 4.Supervisor.SupID.students.ID
        '''
        exist_log = None
        #if type is conversion or certification
        logbook_type_C = self.Training_Types.capitalize() 
        logbook_type_R = self.Training_Types_Re.capitalize()
        if '_' in logbook_type_R:    
            logbook_type_R = logbook_type_R.replace(' ','_')
            recertf = logbook_type_R.split('_')[0]
            pathway = logbook_type_R.split('_')[1]
            logbook_type_R = recertf.capitalize() + '_' + pathway.capitalize()
        if 'Certification' in logbook_type_C:
            logbook_type_C = 'Certification'
        if 'Conversion' in logbook_type_C:
            logbook_type_C = 'Conversion'
        exist_log = manager.db.child("Logbook").child(self.logbook_id)
        check = exist_log.get().each()
        #if not overwrite, first check if logbook existed
        if not overwrite:
            #no logbook, creat certification + status
            if manager.db.child("Logbook").child(self.logbook_id).get().val() == None:
                if logbook_type_C == 'Certification':
                    self.log_create(logbook_type_C)
                    self.result = {"fulfillmentText":"Great, your new <strong>"+logbook_type_C+"</strong> logbook is created! You can type <strong>export</strong> to download your logbooks!"}
                else:
                    self.result = {"fulfillmentText":"Sorry, you are only allowed to participate in <strong>Certification</strong> training at this stage!"}
                return self.result
            #one logbook has to be certification
            elif len(check) == 1:
                exist = check[0].key()
                #if still asking for certification
                if logbook_type_C == exist:
                    self.result = {"fulfillmentText":"I note that you have already have an existing <strong>"+logbook_type_C.capitalize()+"</strong> \
                    logbook, do you still need to create a new one? [this operation will <strong>OVERWIRTE</strong> the existing logbook]!"}
                    return self.result
                #if asking for recertification
                if logbook_type_R or logbook_type_C == 'Conversion':
                    #check1: 3 year
                    start = manager.db.child("Logbook").child(self.logbook_id).child('Certification').child('start').get().val()
                    start_date = datetime.strptime(start, '%d/%m/%Y')
                    end_date = date(start_date.year + 3, start_date.month, start_date.day) 
                    end_date = end_date.strftime('%d/%m/%Y')
                    today =  datetime.strptime(date.today().strftime('%d/%m/%Y'),'%d/%m/%Y')#datetime
                    end_date = datetime.strptime(end_date,'%d/%m/%Y')
                    check_date = 'PASS' if end_date <= today else "<br>* You havn't accomplished Certification training, this will be due on {0}".format(end_date.strftime('%d/%m/%Y'))
                    #check2: verified?
                    verify = manager.db.child("Logbook").child(self.logbook_id).child('Certification').child('verified').get().val()
                    check_verify = 'PASS' if verify != '' else "<br>* The number of verified logbook cases does not meet requirment"
                    print('check 1',check_date,'check 2',check_verify)
                    if check_date=='PASS' and check_verify=='PASS':
                        if logbook_type_R:
                            self.result = {"fulfillmentText":"Alright, can you specifiy which <strong>pathway</strong> of Recertification do you want?"}
                        elif logbook_type_C:
                            self.log_create(logbook_type_C)
                            self.result = {"fulfillmentText":"Great, your new <strong>"+logbook_type_C+"</strong> logbook is created! You can type <strong>export</strong> to download your logbooks!" }                    
                    else:
                        check_date = '' if check_date=='PASS' else check_date
                        check_verify = '' if check_verify=='PASS' else check_verify
                        self.result = {"fulfillmentText":"Sorry, you are not eligible to apply for <strong>Recertification or Conversion</strong> traing now. As you have not met all the requirments for them:<br>{0}{1}".format(check_date,check_verify)}
                    return self.result
            #two logbook: can create recertification or conversion
            elif len(check) == 2:
                if logbook_type_C == 'Certification':
                    self.result = {"fulfillmentText":"You are not allowed to have two Certification logbooks!"}
                for logbook in check:
                    if logbook.key() == 'Recertification_Pathway1' or logbook.key() == 'Recertification_Pathway2':
                        if logbook_type_C == "Conversion":
                            if self.role == 'A':
                                manager.db.child('Identification').child(self.ids).child('Program').set(logbook.key() + ', Conversion')
                                self.log_create(logbook_type_C)
                                self.result = {"fulfillmentText":"Great, your new <strong>"+logbook_type_C+"</strong> logbook is created! You can type <strong>export</strong> to download your logbooks!"}
                            else:
                                self.result = {"fulfillmentText":"Sorry, you are already a Level B specialist." }
                        if logbook_type_R:
                            self.result = {"fulfillmentText":"Alright, can you specifiy which <strong>pathway</strong> of Recertification do you want?"}
                        return self.result                           
                    elif logbook.key() == "Conversion":
                        if logbook_type_R:
                            self.result = {"fulfillmentText":"Alright, can you specifiy which <strong>pathway</strong> of Recertification do you want?"}
                        if logbook_type_C == "Conversion":
                            self.result = {"fulfillmentText":"I note that you have already have an existing <strong>"+logbook_type_C.capitalize()+"</strong> \
                            logbook, do you still need to create a new one? [this operation will <strong>OVERWIRTE</strong> the existing logbook]!"}
                        return self.result 
            
            elif len(check) > 2:
                if logbook_type_C == 'Certification':
                    self.result = {"fulfillmentText":"You are not allowed to have two Certification logbooks!"}
                if logbook_type_C == 'Conversion':
                    self.result = {"fulfillmentText":"I note that you have already have an existing <strong>"+logbook_type_C.capitalize()+"</strong> \
                    logbook, do you still need to create a new one? [this operation will <strong>OVERWIRTE</strong> the existing logbook]!"}          
                if logbook_type_R:
                    self.result = {"fulfillmentText":"Alright, can you specifiy which <strong>pathway</strong> of Recertification do you want?"}
                return self.result 
        elif overwrite:
            #if logbook is not recertification
            if logbook_type_C:
                #created an achived copy 
                print('ONVERWRITE certificaion or conversion')
                ached_content = manager.db.child('Logbook').child(self.logbook_id).child(logbook_type_C).get().val()
                ached_status = manager.db.child('Status').child(self.ids).child(logbook_type_C).get().val()
                manager.db.child('Logbook_backup').child(self.logbook_id).child(logbook_type_C).child(str(date.today().strftime('%d-%m-%Y'))).child('logbook').set(ached_content)
                manager.db.child('Logbook_backup').child(self.logbook_id).child(logbook_type_C).child(str(date.today().strftime('%d-%m-%Y'))).child('status').set(ached_status)
                #remove org logbook/empty status
                manager.db.child('Status').child(self.ids).child(logbook_type_C).remove()
                manager.db.child("Logbook").child(self.logbook_id).child(logbook_type_C).remove()
                self.log_create(logbook_type_C)
                self.result = {"fulfillmentText":"Great, your new <strong>"+logbook_type_C+"</strong> logbook is created! You can type <strong>export</strong> to download your logbooks!"}
            #if logbook is recertification
            elif logbook_type_R:
                pathway = self.para.get("pathway")
                print('ONVERWRITE recertification')
                ached_content = manager.db.child('Logbook').child(self.logbook_id).child("Recertification"+'_'+'Pathway'+str(pathway)).get().val()
                ached_status = manage.db.child('Status').child(self.ids).child("Recertification"+'_'+'Pathway'+str(pathway)).get().val()
                manager.db.child('Logbook_backup').child(self.logbook_id).child("Recertification"+'_'+'Pathway'+str(pathway)).child(str(date.today().strftime('%d-%m-%Y'))).child('logbook').set(ached_content)
                manager,db.child('Logbook_backup').child(self.logbook_id).child("Recertification"+'_'+'Pathway'+str(pathway)).child(str(date.today().strftime('%d-%m-%Y'))).child('status').set(ached_status)
                #remove org logbook/empty status
                manager.db.child('Status').child(self.ids).child("Recertification"+'_'+'Pathway'+str(pathway)).remove()
                manager.db.child("Logbook").child(self.logbook_id).child("Recertification"+'_'+'Pathway'+str(pathway)).remove()
                self.log_create("Recertification"+'_'+'Pathway'+str(pathway),pathway=pathway)
                self.result = {"fulfillmentText":"Sure, your new <strong>{0}<strong> logbook with pathway <strong>{1}</strong> is created! You can type <strong>export</strong> to download your logbooks!".format("Recertification",pathway)}
            return self.result

    def create_intent_qa(self,display_name, training_phrases_parts,action,paramaters):
        """
        Function used to create an intent of the given intent type.
        Input: display_name, training_phrases_parts,action,paramaters of the intent
        """
        intents_client = dialogflow.IntentsClient()
        project_id = os.getenv('DIALOGFLOW_PROJECT_ID')
        parent = intents_client.project_agent_path(project_id)
        intents = intents_client.list_intents(parent)
        for i in intents:
            if i.display_name == display_name:
                print('intent already exists')
                return
        training_phrases = []
        for training_phrases_part in training_phrases_parts:
            part = dialogflow.types.Intent.TrainingPhrase.Part(text=training_phrases_part)
            training_phrase = dialogflow.types.Intent.TrainingPhrase(parts=[part])
            training_phrases.append(training_phrase)
        intent_paras = []
        for para in paramaters:
            if para != "Training_Types" and para != "Training_Types_Re":
                entity = '@sys.date' if para == "Date" else '@sys.any'
                prompts = 'Can you tell me the {0} of the report?'.format(para)
                para = para.replace(' ','_')
                para = para.replace('+','_')
                para = para.replace('_Supervising','Supervisor')
                if len(para) > 30:
                    temp = ''.join(c for c in para if c.isupper())
                    para = temp
                intent_para = dialogflow.types.Intent.Parameter(name='',display_name=para,entity_type_display_name=entity,mandatory=True,prompts=[prompts])
                intent_paras.append(intent_para)
        intent = dialogflow.types.Intent(
            display_name=display_name,
            training_phrases=training_phrases,
            parameters=intent_paras,
            action=action,
            webhook_state=dialogflow.types.Intent.WebhookState.WEBHOOK_STATE_ENABLED_FOR_SLOT_FILLING,
            input_context_names=["projects/logbook-assistant-cafdge/agent/sessions/cc_CTCA000012/contexts/logbook_entry_qa"]
            )
        response = intents_client.create_intent(parent, intent)
        print('Intent created: {}'.format(response))

    def exportExcel(self,logbook_type):
        '''
        Function used for exporting excels 
        Input: Logbook type
        Output: Generate logbook excel in server under userLogbooks folder
        '''
        #Hyper-parameters
        filename = "./userLogbooks/CTCA_{0}_Logbook_{1}.xls".format(logbook_type,self.logbook_id)
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
        #1. grab data from logbook
        d_index = {}
        schema = schemaExtraction.logbook_entry(logbook_type)
        if ' Supervising' in list(schema.keys()):
            schema['Supervising'] = schema.pop(' Supervising')
        schema = list(schema.keys())
        #2. create xls schema
        for i in range(len(schema)):
            d_index[schema[i]] = i
            outSheet.write(0,i,schema[i],style=style_h)
        #3. fill in logbook content
        counter = 1
        content = manager.db.child('Logbook').child(self.logbook_id).child(logbook_type).get().val()
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

    def responses(self):

        '''
        Main Function used to generate chatbot responses
        Responses are generated based on action names
        UserInput -> Matched Intents -> Response based on Intent.action
        '''
        #==============init dialog==============
        if self.action == 'smalltalk.greetings.hello':
            supervision = '<br>-<strong>Logbook Supervision</strong>' if self.role == 'B' else ''
            self.result = {"fulfillmentText": "Greetings! "+self.name+", I am your Logbook Assistant, I can help you with<br>-<strong>Logbook Creation</strong>\
            <br>-<strong>Logbook Records Display</strong><br>-<strong>Logbook Editing</strong><br>-<strong>Find Supervisor</strong>" + supervision + "<br>You can also:<br>Type <strong>\
            status</strong> at any time to check your training progress<br>Type <strong>export</strong> to download logbooks"}
         #==============logbook status==============
        if self.action == 'logbook_status':
            status = manager.db.child('Status').child(self.ids).get().val()
            if not status:
                detail = "<br>You have no active training."
                Training,end_date = 'N/A','N/A'
            else:
                certification = status['Certification'] if 'Certification' in status else ''
                conversion = status['conversion'] if 'conversion' in status else ''
                rp1 = status['Recertification_Pathway1'] if 'Recertification_Pathway1' in status else ''
                rp1 = status['Recertification_Pathway2'] if 'Recertification_Pathway2' in status else ''
                if certification:
                    end_date = certification['end']
                    if self.role == 'A':
                        Training = 'Level A Certification'
                        detail = '<br><strong>For your Level A Certification:</strong><br>' + str(certification['total'])+ '/150 cases completed with<br>'+str(certification['Live'])+'/50 live cases<br>'+str(certification['Case_from_CT_course'])+'/25 cases from CT course<br>' + str(certification['Correlated'])+'/50 correlated cases<br>'+str(certification['Non-coronary_cardiac_findings']) + '/25 cases with Non-coronary cardiac findings<br>'+str(certification['Non-cardiac_findings'])+'/25 cases with Non-cardiac findings'
                    elif self.role == 'B':
                        Training = 'Level B Certification'
                        detail = '<br><strong>For your Level B Certification:</strong><br>' + str(certification['total'])+ '/300 cases completed with<br>'+str(certification['Live'])+'/80 live cases<br>'+str(certification['Case_from_CT_course'])+'/25 cases from CT course<br>' + str(certification['Correlated'])+'/30 correlated cases'
                elif rp1:
                    end_date = rp1['end']
                    if self.role == 'A':
                        Training = 'Level A Recertification Pathway1'
                        detail = '<br><strong>For your Level A Recertification Pathway1:</strong><br>' + str(rp1['total']) + '/300 cases completed with<br>'+str(rp1['Correlated'])+'/30 correlated cases<br>'+str(rp1['CT_course_Library'])+'/100 cases from CT course or Library'
                    elif self.role == 'B':
                        Training = 'Level B Recertification Pathway1'
                        detail = '<br><strong>For your Level B Recertification Pathway1:</strong><br>' + str(rp1['total']) + '/600 cases completed with<br>'+str(rp1['Correlated'])+'/50 correlated cases<br>'+str(rp1['CT_course_Library'])+'/200 cases from CT course or Library' 
                elif rp2:
                    end_date = rp2['end']
                    if self.role == 'A':
                        Training = 'Level A Recertification Pathway2'
                        detail = '<br><strong>For your Level A Recertification Pathway2:</strong><br>' + str(rp2['Live_Cases']) + '/150 live cases completed with<br>'+str(rp2['Correlated'])+'/30 correlated cases'
                    if self.role == 'B':
                        Training = 'Level B Recertification Pathway2'
                        detail = '<br><strong>For your Level B Recertification Pathway2:</strong><br>' + str(rp2['Live_Cases']) + '/400 live cases completed with<br>'+str(p2['Correlated'])+'/50 correlated cases'
                if conversion:
                    Training+='; LevelA to LeveB Conversion'
                    detail += '<br><strong>For your Level A to Level B conversion:</strong><br>' + str(conversion['total']) + '/150 additional cases completed with<br>'+str(conversion['Live'])+'/50 live cases<br>'+ str(conversion['Correlated'])+'/30 correlated cases'

            rst = '<strong>Name:</strong> {0}<br><strong>ID:</strong> {1}<br><strong>Training:</strong> {2}<br><strong>Due Date:</strong> {3}'.format(self.name,self.ids,Training,str(end_date))
            rst += detail
            self.result = {"fulfillmentText":rst}
        #==============logbook create==============
        if self.action == 'logbook_create' or self.action == 'logbook_create_any':
            self.result = {"fulfillmentText":"Sure, please select training type from below:<br><strong>Certification</strong><br><strong>Recertification</strong><br><strong>Conversion</strong>"} 
        #==============logbook create confirm type==============
        if self.action == 'logbook_req_confirm':
            pre,certA,certB,recertA,recertB,conv,sub = '','','','','','',''
            queryType = self.Training_Types if self.Training_Types else self.Training_Types_Re

            if queryType == 'Certification':
                self.result = {"fulfillmentText": "Please carefully read through Certification Training Requirments from <br><a href='{0}/mainpage.html#/dash1'>Here</a><br>Type <strong>Yes</strong> to agree. <strong>Cancel</strong> to stop.".format(self.NAT)}
            elif queryType == 'Conversion':
                self.result = {"fulfillmentText": "Please carefully read through Conversion Training Requirments from <br><a href='{0}/mainpage.html#/dash3'>Here</a><br>Type <strong>Yes</strong> to agree. <strong>Cancel</strong> to stop.".format(self.NAT)}
            else:
                self.result = {"fulfillmentText": "Please carefully read through Recertification Training Requirments from <br><a href='{0}/mainpage.html#/dash2'>Here</a><br>Type <strong>Yes</strong> to agree. <strong>Cancel</strong> to stop.".format(self.NAT)}
        #==============logbook req confirm ==============
        if self.action == 'logbook_create_confirm':
            self.result = self.log_type_return()
        #==============logbook create confirm type-recertification==============
        if self.action == 'logbook_create_confirm_rec':
            pathway = self.para.get("pathway")
            pathway_rest = 1 if pathway==2 else 2
            logbook_type = self.Training_Types_Re.capitalize()
            logbook_type_curr = logbook_type + '_Pathway' + str(pathway)
            logbook_type_rest = logbook_type + '_Pathway' + str(pathway_rest)
            #####FUTURE WORK adter first 6 years################
            # exist = db.child('Logbook').child(logbook_id).get().val().keys()
            # exist_recertify,check_date,check_verify = '','',''
            # if logbook_type_curr in exist:
            #     exist_recertify = logbook_type_curr
            # elif logbook_type_rest in exist:
            #     exist_recertify = logbook_type_rest
            # start = db.child("Logbook").child(logbook_id).child(exist_recertify).child('start').get().val()
            # start_date = datetime.strptime(start, '%d/%m/%Y')
            # end_date = date(start_date.year + 3, start_date.month, start_date.day) 
            # end_date = end_date.strftime('%d/%m/%Y')
            # today =  datetime.strptime(date.today().strftime('%d/%m/%Y'),'%d/%m/%Y')#datetime
            # end_date = datetime.strptime(end_date,'%d/%m/%Y')
            # print('end is ',end_date,'start is ',today)
            # check_date = 'PASS' if end_date <= today else ""
            # #check2: verified?
            # verify = db.child("Logbook").child(logbook_id).child('Certification').child('verified').get().val()
            # check_verify = 'PASS' if verify != '' else ""
            if manager.db.child("Logbook").child(self.logbook_id).child(logbook_type_curr).get().val():#if current recertification exist
                self.result = {"fulfillmentText": "I note that you have already have an existing <strong>"+logbook_type_curr+"</strong> \
                logbook, do you still need to create a new one? [this operation will <strong>OVERWIRTE</strong> the existing logbook]!"}            
            elif manager.db.child("Logbook").child(self.logbook_id).child(logbook_type_rest).get().val():#if recertification of another pathway exist
                self.result = {"fulfillmentText": "Are you sure you want to change from <strong>Recertification Pathway{0}</strong> to <strong>Recertification Pathway{1}</strong>[Type <strong>Transfer</strong> to make this change happen]".format(pathway_rest,pathway)}
            else:#if no recertification exist
                if 'Conversion' in exist:
                    manager.db.child('Identification').child(self.ids).child('Program').set(logbook_type_curr + ', Conversion')
                else:
                    manager.db.child('Identification').child(self.ids).child('Program').set(logbook_type_curr)
                self.log_create(logbook_type_curr,pathway=pathway)
                self.result = {"fulfillmentText": "Sure, your new <strong>{0}</strong> logbook with pathway <strong>{1}</strong> is created! You can type <strong>export</strong> to download your logbooks!".format("Recertification",pathway)}
    #==============logbook create confirm recer transfer==============
        if self.action == 'logbook_create_recer_conv':
            pathway = para.get("pathway")
            pathway_org = 1 if pathway==2 else 2
            logbook_type  = 'Recertification'+ '_Pathway' + str(pathway)
            exist = manager.db.child('Logbook').child(self.logbook_id).get().val().keys()
            if 'Conversion' in exist:
                manager.db.child('Identification').child(self.ids).child('Program').set(logbook_type + ', Conversion')
            else:
                manager.db.child('Identification').child(self.ids).child('Program').set(logbook_type)
            ached_content = manager.db.child('Logbook').child(self.logbook_id).child(logbook_type).get().val()
            ached_status = manager.db.child('Status').child(self.ids).child(logbook_type).get().val()
            manager.db.child('Logbook_backup').child(self.logbook_id).child(logbook_type).child(str(date.today().strftime('%d-%m-%Y'))).child('logbook').set(ached_content)
            manager.db.child('Logbook_backup').child(self.logbook_id).child(logbook_type).child(str(date.today().strftime('%d-%m-%Y'))).child('status').set(ached_status)
            #remove org logbook
            manager.db.child('Status').child(self.ids).child(logbook_type).remove()
            manager.db.child("Logbook").child(self.logbook_id).child(logbook_type).remove()
            self.log_create(logbook_type,pathway=pathway)
            self.result = {"fulfillmentText": "Sure, you have successfully changes from <strong>Recertification Pathway{0}</strong> to <strong>Recertification Pathway{1}</strong>".format(pathway_org,pathway)}
        #==============logbook overwrite==============
        if self.action == "confirm_overwrite":
            self.result = self.log_type_return(overwrite=True)
        #==============logbook overwrite decline==============
        if self.action == "decline_overwrite":
            self.result = {"fulfillmentText": "Sure, I will keep your original logbbok as it is."}
        #==============logbook show==============
        if self.action == 'logbook_show':
            #prompt user to create a new logbook
            if manager.db.child("Logbook").child(self.logbook_id).get().val() is None:
                self.result = {"fulfillmentText": "Sorry, you have no recorded logbook in the system, please type <strong>'create'</strong> to create a new one"}
            #if a user has more than one logbooks
            elif len(manager.db.child("Logbook").child(self.logbook_id).get().each())>1:
                logbook_types = manager.db.child("Logbook").child(self.logbook_id).get().each()
                logbooks = ''
                for i in range(len(logbook_types)-1):
                    logbooks += logbook_types[i].key() + ', '
                logbooks += logbook_types[-1].key()
                self.result = {"fulfillmentText": "I note that you have <strong>{0}</strong> logbooks in our system, can you tell me which one you want to display".format(logbooks)}

            else:
                logbook_types = manager.db.child("Logbook").child(self.logbook_id).get().each()
                num_cases = manager.db.child("Logbook").child(self.logbook_id).child(logbook_types[0].key()).get().each()
                self.result = {"fulfillmentText": "Sure, I noted that you have one <strong>{0}</strong> logbook, please type <strong>{1}</strong> to show details".format(logbook_types[0].key(),logbook_types[0].key())}
        #==============logbook show selection==============
        if self.action == 'logbook_show_select':
            show_one = self.para.get('Training_Types')
            num_logbooks = manager.db.child("Logbook").child(self.logbook_id).get().each()
            num_cases = manager.db.child("Logbook").child(self.logbook_id).child(show_one).get().each()
            print('what is show one ',show_one)
            print('num case is ',num_cases)
            if len(num_cases) == 2:
                self.result = {"fulfillmentText":"Sure, you have <strong>{2}</strong> logbook(s)<br>your </strong>{0}</strong> logbook has <strong>0</strong> records.<br>Details can be checked from <br><a onclick=simuclick() href='{3}/mainpage.html#/{1}'>Here</a>".format(show_one,show_one,len(num_logbooks),self.NAT)}
            else:
                org_max = len(num_cases)-2#num_cases[-3].key()
                self.result = {"fulfillmentText": "Sure, you have <strong>{3}</strong> logbook(s)<br>your </strong>{0}</strong> logbook has <strong>{1}</strong> records.<br>Details can be checked from <br><a onclick=simuclick() href='{4}/mainpage.html#/{2}'>Here</a>".format(show_one,org_max,show_one,len(num_logbooks),self.NAT)}
             #==============logbook edit==============
        if self.action == 'logbook_edit':
            #prompt user to create a new logbook
            if manager.db.child("Logbook").child(self.logbook_id).get().val() is None:
                self.result = {"fulfillmentText": "Sorry, you have no recorded logbook in the system, please type <strong>'create'</strong> to create a new one"}
            #if a user has more than one logbooks
            elif len(manager.db.child("Logbook").child(self.logbook_id).get().each())>1:
                logbook_types = manager.db.child("Logbook").child(self.logbook_id).get().each()
                logbooks = ''
                for i in range(len(logbook_types)-1):
                    logbooks += logbook_types[i].key() + ', '
                logbooks += logbook_types[-1].key()
                self.result = {"fulfillmentText": "I note that you have <strong>{0}</strong> logbooks in our system, can you tell me which one you want to edit".format(logbooks)}
            else:
                logbook_types = manager.db.child("Logbook").child(self.logbook_id).get().each()
                self.result = {"fulfillmentText": "Sure, just type <strong>{0}</strong> to edit".format(logbook_types[0].key())}
        #==============logbook edit confirm==============
        if self.action == 'logbook_edit_comfirm':
            logbook_types = manager.db.child('Logbook').child(self.logbook_id).get().each()
            query_logbook = self.Training_Types_Re if self.Training_Types_Re else self.Training_Types
            #set upload schema in db:
            manager.db.child('Identification').child(self.ids).update({'Upload':query_logbook})
            if '_' in query_logbook:
                temp_1 = query_logbook.split('_')
                temp_2 = list(map(lambda a:a.capitalize(),temp_1))
                query_logbook = '_'.join(temp_2)
            flag = False
            for log in logbook_types:
                if log.key() == query_logbook:
                    self.result = {"fulfillmentText": "Sure, which operation do you want?<br>- <strong>logbook Entry</strong><br>- <strong>logbook Deletion</strong><br>- <strong>logbook Recover</strong>"}
                    flag = True
                    break
            if not flag:
                self.result = {"fulfillmentText": "Sorry, I can't find any <strong>{0}</strong> logbooks under your account<br>Please type <strong>create</strong> to create new {1} logbook.".format(query_logbook,query_logbook)}
        #==============logbook edit entry==============
        if self.action == 'logbook_edit_entry':
            logbook_type_C = self.Training_Types
            logbook_type_R = self.Training_Types_Re
            #extract schemas
            schema = {}
            action_give = ''
            intent_name = ''

            if logbook_type_C:
                schema = schemaExtraction.logbook_entry(logbook_type_C)
                schema['Training_Types'] = logbook_type_C.capitalize()
                train_phrase = [logbook_type_C, logbook_type_C.capitalize()]
                action_give = 'logbook_edit_entry_QA_{0}'.format(logbook_type_C.capitalize())
                intent_name = 'Logbook_Assistant.entry.QA.{0}'.format(logbook_type_C.capitalize())
                
            if logbook_type_R:
                logbook_type_R = logbook_type_R.replace(' ','_')
                recertf = logbook_type_R.split('_')[0]
                pathway = logbook_type_R.split('_')[1][-1]
                schema = schemaExtraction.logbook_entry(recertf.capitalize(),path_way=pathway)
                schema['Training_Types_Re'] = logbook_type_R
                train_phrase = [logbook_type_R, logbook_type_R.capitalize()]
                action_give = 'logbook_edit_entry_QA_{0}'.format(logbook_type_R.capitalize())
                intent_name = 'Logbook_Assistant.entry.QA.{0}'.format(logbook_type_R.capitalize())
            paramaters=list(schema.keys())
            self.create_intent_qa(intent_name,train_phrase,action_give,paramaters)

            if '_' in logbook_type_R:
                temp_1 = logbook_type_R.split('_')
                temp_2 = list(map(lambda a:a.capitalize(),temp_1))
                logbook_type_R = '_'.join(temp_2)
            self.result = {"output_contexts": [{'name': 'projects/logbook-assistant-cafdge/agent/sessions/cc_CTCA000012/contexts/logbook_entry_upload', 
            'lifespanCount': 1, 'parameters': {'Training_Types': logbook_type_C, 'Training_Types_Re': logbook_type_R}}, 
            {'name': 'projects/logbook-assistant-cafdge/agent/sessions/cc_CTCA000012/contexts/logbook_entry_qa', 'lifespanCount': 1, 'parameters': schema}],
            "fulfillmentText":"Sure, <br>- Simply upload your report using the <strong>upload button</strong> OR<br>- type <strong>{0}{1}</strong> to enter a logbook case via Q/A dialog<br>".format(logbook_type_C,logbook_type_R)}

        #==============logbook edit entry==============
        if self.action == 'logbook_edit_entry_QA_Recertification_pathway1' or self.action == 'logbook_edit_entry_QA_Recertification_pathway2' or self.action == 'logbook_edit_entry_QA_Certification' or self.action == 'logbook_edit_entry_QA_Conversion':
            rst = ''
            for k in self.para:
                if self.para[k]=='' and k != "Training_Types" and k != "Training_Types_Re":
                    if k == 'Correlated':
                        self.result = {"fulfillmentText": 'Can you tell me if report is <strong>{0}</strong>?<br>[1 for yes, 0 for no, N/A for unknown]'.format(k)}
                    elif k == 'Co_reporting':
                        self.result = {"fulfillmentText": 'Can you tell me the name(s) <strong>Co-reporter</strong> of the report?'}
                    elif k == 'Supervising':
                        self.result = {"fulfillmentText": 'Can you tell me the name(s) <strong>Supervisor</strong> of the report?'}
                    elif k == 'Case_from_CT_course':
                        self.result = {"fulfillmentText": 'Can you tell me if the case is from a <strong>CT course</strong>?<br>[1 for yes, 0 for no, N/A for unknown]'}
                    elif k == 'Live'or k=='Library'or k=='Live_Cases':
                        k = k.split('_')[0] if '_' in k else k
                        self.result = {"fulfillmentText": 'Can you tell me if report is from a <strong>{0}</strong> case?<br>[1 for yes, 0 for no, N/A for unknown]'.format(k)}
                    elif k == 'Non-cardiac_findings':
                        self.result = {"fulfillmentText":'Can you tell me if report contains any <strong>Non cardiac findings</strong>?<br>[1 for yes, 0 for no, N/A for unknown]'}
                    elif k == 'Non-coronary_cardiac_findings':
                        self.result = {"fulfillmentText": 'Can you tell me if report contains any <strong>Non coronary cardiac findings</strong>?<br>[1 for yes, 0 for no, N/A for unknown]'}
                    elif k == 'Graft_Or_Thoracic_Aorta':
                        self.result = {"fulfillmentText": 'Can you tell me if this is a <strong>Graft/Thoracic Aorta</strong> case?<br>[1 for yes, 0 for no, N/A for unknown]'}
                    elif k == 'Native_Coronary':
                        self.result = {"fulfillmentText": 'Can you tell me if this is a <strong>Native Coronary</strong> case?<br>[1 for yes, 0 for no, N/A for unknown]'}
                    else:
                        k = ' '.join(k.split('_')) if '_' in k else k
                        self.result = {"fulfillmentText": 'Can you tell me the <strong>{0}</strong> of your report?'.format(k)}
                    rst = True
                    break
            if not rst:
                rst += 'Thank, you are about to enter a new case to your logbook, can you check if these information are corrected?<br>'
                org_date = self.para['Date']
                format_date = re.findall(r"\d{4}-\d+-\d+",org_date)
                format_str = '%Y-%m-%d'
                datetime_obj = datetime.strptime(format_date[0], format_str)
                self.para['Date'] = datetime_obj.strftime('%d/%m/%Y')
                for k in self.para:
                    if  k != "Training_Types" and k != "Training_Types_Re":
                        rst += '<br><strong>{0} : {1}</strong>'.format(k,self.para[k])
                rst += '<br><br> Type <strong>Yes</strong> to continue creating or <strong>No</strong> to stop'
                self.result = {"fulfillmentText": rst}   
        #==============logbook edit entry confirm create new case==============
        if self.action == 'logbook_edit_entry_QA_confirm':
            logbook_type = self.Training_Types if self.Training_Types else self.Training_Types_Re
            if '_' in logbook_type:
                temp_1 = logbook_type.split('_')
                temp_2 = list(map(lambda a:a.capitalize(),temp_1))
                logbook_type = '_'.join(temp_2)

            out_context = self.req.get('queryResult').get('outputContexts')
            for context in out_context:
                if context['name'].split('/')[-1] == 'logbook_entry_qa_confirm':
                    para_all = context['parameters']

            records_count = manager.db.child("Logbook").child(self.logbook_id).child(logbook_type).get().each()
            ###change date format
            new_para = {k:para_all[k] for k in para_all if not re.match('.*original',k) and not re.match('Training.*',k)}
            print('parameter is ',new_para)
            org_date = new_para['Date']
            format_date = re.findall(r"\d{4}-\d+-\d+",org_date)
            format_str = '%Y-%m-%d'
            datetime_obj = datetime.strptime(format_date[0], format_str)
            new_para['Date'] = datetime_obj.strftime('%d/%m/%Y')
            #first record
            if len(records_count) == 2:#and db.child("Logbook").child(logbook_id).child(logbook_type).child(1).child('Date').get().val() == ''
                print('first record')
                manager.db.child("Logbook").child(self.logbook_id).child(logbook_type).child(1).set(new_para)
                numberCases = 1#len(records_count) - 2
            else:#already have some records
                print('more records')
                org_max = records_count[-3].key()
                numberCases = int(org_max)+1
                manager.db.child("Logbook").child(self.logbook_id).child(logbook_type).child(numberCases).set(new_para)
            # #update status
            status = manager.db.child('Status').child(self.ids).child(logbook_type).get().val()
            if logbook_type == 'Certification':
                status['Live'] += int(new_para['Live']) if new_para['Live'] == '1' else 0
                status['Case_from_CT_course'] += int(new_para['Case_from_CT_course']) if new_para['Case_from_CT_course'] == '1' else 0
                status['Correlated'] += int(new_para['Correlated']) if new_para['Correlated'] == '1' else 0
                status['Non-cardiac_findings'] += int(new_para['Non-cardiac_findings']) if new_para['Non-cardiac_findings'] == '1' else 0
                status['Non-coronary_cardiac_findings'] += int(new_para['Non-coronary_cardiac_findings']) if new_para['Non-coronary_cardiac_findings'] == '1' else 0

            elif logbook_type == 'Conversion' or logbook_type == 'Recertification_Pathway2':
                status['Live'] += int(new_para['Live']) if new_para['Live'] == '1' else 0
                status['Correlated'] += int(new_para['Correlated']) if new_para['Correlated'] == '1' else 0
            elif logbook_type == 'Recertification_Pathway1':
                if new_para['Case_from_CT_course'] == '1' or new_para['Library'] == '1':
                    status['CT_course_Library'] += 1
                status['Correlated'] += int(new_para['Correlated']) if new_para['Correlated'] == '1' else 0

            status['total'] += 1
            manager.db.child('Status').child(self.ids).child(logbook_type).set(status)
            self.result = {"fulfillmentText":"Great, now you have <strong>{0}</strong> cases in your <strong>{1}<strong> logbook! <br>Detail can be checked from <a onclick=simuclick() href='{3}/mainpage.html#/{2}'>Here</a>".format(status['total'], logbook_type,logbook_type,self.NAT)}
        #==============logbook edit entry decline ==============   
        if self.action == 'logbook_edit_entry_QA_decline':
            self.result = {"fulfillmentText": 'Sure, type <strong>{0}{1}</strong> to answer my questions again <br>OR<br>upload your report and I can help you with this.'.format(self.para.get('Training_Types'),self.para.get('Training_Types_Re'))}
        #==============logbook edit delete ==============
        if self.action == 'logbook_remove_confirm':
            logbook_type = self.Training_Types if self.Training_Types else self.Training_Types_Re
            self.result = {"fulfillmentText": "Are you sure you want to delete {0} logbook?".format(logbook_type)}
        #==============logbook edit delete confirm==============
        if self.action == 'logbook_remove':
            logbook_type = self.Training_Types if self.Training_Types else self.Training_Types_Re
            logbook_type_with_comma = logbook_type+','
            #update logbook,status,identification,supervisor table====>
            #cached original data
            ached_content = manager.db.child('Logbook').child(self.logbook_id).child(logbook_type).get().val()
            ached_status = manager.db.child('Status').child(self.ids).child(logbook_type).get().val()
            ached_id = manager.db.child('Identification').child(self.ids).child('Program').get().val()
            supID = manager.db.child('Trainee').child(self.ids).child('SupervisorUserID').get().val()
            ached_sup = manager.db.child('Supervisor').child(supID).child('Students').child(self.ids).get().val()
     
            #set delete time 
            manager.db.child('Logbook_backup').child(self.logbook_id).child(logbook_type).child(str(date.today().strftime('%d-%m-%Y'))).child('logbook').set(ached_content)
            manager.db.child('Logbook_backup').child(self.logbook_id).child(logbook_type).child(str(date.today().strftime('%d-%m-%Y'))).child('status').set(ached_status)
            #remove org logbook
            manager.db.child('Status').child(self.ids).child(logbook_type).remove()
            manager.db.child("Logbook").child(self.logbook_id).child(logbook_type).remove()
            updatedId = ached_id.replace(logbook_type_with_comma,'') if logbook_type_with_comma in ached_id else ached_id.replace(logbook_type,'')
            updatedSup = ached_sup.replace(logbook_type_with_comma,'') if logbook_type_with_comma in ached_sup else ached_sup.replace(logbook_type,'')
            manager.db.child('Identification').child(self.ids).child('Program').set(updatedId)
            manager.db.child('Supervisor').child(supID).child('Students').child(self.ids).set(updatedSup)

            self.result = {"fulfillmentText": "No problem, your {0} logbook is now removed.".format(logbook_type)}
        #==============logbook edit delete decline==============
        if self.action == 'logbook_remove_decline':
            logbook_type_C = para.get('Training_Types')
            logbook_type_R = para.get('Training_Types_Re')
            logbook_type = logbook_type_C if logbook_type_C else logbook_type_R
            self.result = {"fulfillmentText": "Sure, I will not remove your {0} logbook.".format(logbook_type)}
        #==============logbook edit recover confirm==============
        if self.action == 'logbook_recover':
            logbook_type = self.Training_Types if self.Training_Types else self.Training_Types_Re
            backups = manager.db.child('Logbook_backup').child(self.logbook_id).child(logbook_type).get().each()
            if not manager.db.child('Logbook_backup').child(self.logbook_id).child(logbook_type).get():
                self.result = {"fulfillmentText": "No records need to be recovered."}
            else:
                timestamps = 'Sure, I have found logbooks deleted on '
                for time in backups:
                    timestamps += "<br><strong>{0}</strong>".format(time.key())
                self.result = {"fulfillmentText": timestamps + "<br>Can you specifiy which one do you want to recover?"}
        #==============logbook edit recover==============
        if self.action == 'logbook_recover_confirm':
            timestamps = self.para.get('date')
            tt = re.findall(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',timestamps)
            querytime =  datetime.strptime(tt[0], '%Y-%m-%d').strftime('%d-%m-%Y')
            logbook_type = self.Training_Types if self.Training_Types else self.Training_Types_Re
            deletedLog = manager.db.child('Logbook_backup').child(self.logbook_id).child(logbook_type).child(querytime).child('logbook').get().val()
            deletedstatus = manager.db.child('Logbook_backup').child(self.logbook_id).child(logbook_type).child(querytime).child('status').get().val()
            if not deletedLog:
                self.result = {"fulfillmentText": "Sorry, no record found on {0}. This might caused by incorrect data format(DD-MM-YYYY) or date not exists.".format(timestamps)}
            else:
                #update logbook,status,identification,supervisor table
                manager.db.child('Logbook').child(self.logbook_id).child(logbook_type).set(deletedLog)
                manager.db.child('Status').child(self.ids).child(logbook_type).set(deletedstatus)
                self.result = {"fulfillmentText":"Sure, your {0} logbook has now been recoved to {1}".format(logbook_type,querytime)}
        #==============logbook supervise==============
        if self.action == 'logbook_supvervise':
            students = manager.db.child("Supervisor").child(self.ids).child("Students").get().val()
            if not students:
                self.result = {"fulfillmentText": "Currently, there is no students under your supervision."}
            else:
                supervisionNumber = len(students.keys())
                unverified_stu = '<br>'
                unverified = 0
                for stu in students:
                    unverified_stu += "<br>"+stu
                    #check if students have unverified logbooks
                    if students[stu] != '':
                        unverified += 1
                        unverified_stu += "<strong> [Need Verified]</strong>"
                if unverified == 0:
                    self.result = {"fulfillmentText": "Currently, there are <strong>{0}</strong> trainees under your supervision and all of them are verified!<br>Details can be check from <strong>Here</strong>"}
                else:
                    self.result = {"fulfillmentText": "Currently, there are <strong>" + str(supervisionNumber) + "</strong> trainees under your supervision, <strong>"+str(unverified)+ "</strong> of them have unverified logbooks."+unverified_stu + "<br><br>Detail can be checked from <strong><a href='{0}/mainpage.html#/supervision'>Here</a></strong>".format(self.NAT)}
        #==============logbook upload==============
        if self.action == 'logbook_upload':
            logbook_type = self.Training_Types if self.Training_Types else self.Training_Types_Re
            doctors = ''
            length = 0
            if '_' in logbook_type:
                recertf = logbook_type.split('_')[0]
                pathway = logbook_type.split('_')[1][-1]
                logbook_type = recertf.capitalize() +'_Pathway'+str(pathway)

            queryText = self.req.get('queryResult').get('queryText')
            if 'Upload_File_Analysis+' in queryText:
                self.reportname =  queryText.split('+')[-1]

            Co_report = self.para.get('Co_report')
            CT_course = self.para.get('CT_course')
            Correlated = self.para.get('Correlated')
            live_lib = self.para.get('live_lib')

            flag = False
            if CT_course == '':
                flag = True
                self.result = {"fulfillmentText": "Is this a case from <strong>CT courses?</strong><br>[1 for yes, 0 for no, N/A for unknown]"}
            elif Correlated == '':
                flag = True
                self.result = {"fulfillmentText": "Is this a <strong>Correlated</strong> case?<br>[1 for yes, 0 for no, N/A for unknown]"}
            elif live_lib == '':
                flag = True
                self.result = {"fulfillmentText": "Can you tell if this is a <strong>Live</strong> or <strong>Library</strong> case?"}

            if not flag:
                live_lib = live_lib.upper()
                live = '1' if live_lib == 'LIVE' else '0'
                lib = '1' if live_lib == 'LIB' or live_lib == 'LIBRARY' else '0'

                org = manager.db.child('Logbook').child(self.logbook_id).child(logbook_type).get().each()
                count = org[-3].key()
                new_count = int(count)
                new_Add = manager.db.child('Logbook').child(self.logbook_id).child(logbook_type).child(new_count).get().val()
                rst = "Thanks, based on your uploaded report <strong>" +self.reportname+"</strong>, I have added following information into your logbook:<br>"

                for k in new_Add.keys():
                    if k == 'Case_from_CT_course':
                        val = CT_course
                        manager.db.child('Logbook').child(self.logbook_id).child(logbook_type).child(new_count).update({k:CT_course})
                    elif k == 'Correlated':
                        val = Correlated
                        manager.db.child('Logbook').child(self.logbook_id).child(logbook_type).child(new_count).update({k:Correlated})
                    elif k == 'Live' or k == 'Live_Cases':
                        val = live
                        manager.db.child('Logbook').child(self.logbook_id).child(logbook_type).child(new_count).update({k:live})
                    elif k == 'Library':
                        val = lib
                        manager.db.child('Logbook').child(self.logbook_id).child(logbook_type).child(new_count).update({k:lib})
                    else:
                        val = new_Add[k]
                        rst += '<br><strong>{0} : {1}</strong>'.format(k,val)
                #update status
                status = manager.db.child('Status').child(self.ids).child(logbook_type).get().val()
                if logbook_type == 'Certification':
                    status['Live'] += int(live)
                    status['Case_from_CT_course'] += int(CT_course) if CT_course == '1' else 0
                    status['Correlated'] += int(Correlated) if Correlated == '1' else 0
                   
                elif logbook_type == 'Conversion' or logbook_type == 'Recertification_Pathway2':
                    status['Live'] += int(live)
                    status['Correlated'] += int(Correlated) if Correlated == '1' else 0
                    
                elif logbook_type == 'Recertification_Pathway1':
                    if CT_course == '1' or lib == '1':
                        status['CT_course_Library'] += 1
                    status['Correlated'] += int(Correlated) if Correlated == '1' else 0
                manager.db.child('Status').child(self.ids).child(logbook_type).set(status)
                rst += "<br> <br>This is case number {0}, you can modify from <a onclick=simuclick() href='{2}/mainpage.html#/{1}'>Here</a>".format(len(org)-2,logbook_type,self.NAT)
                self.result = {"fulfillmentText": rst}
        #==============logbook export confirm==============
        if self.action == 'logbook_export_type_confirm':
            logbook_type = manager.db.child("Logbook").child(self.logbook_id).get().each()
            logbooks = ''
            if logbook_type == None:
                self.result = {"fulfillmentText":"Sorry, currently you have no logbooks, please type <strong>create</strong> to create logbooks!"}
            elif len(logbook_type)==1:
                #generate or update logbook
                filename_unq = "CTCA_{0}_Logbook_{1}.xls".format(logbook_type[0].key(),self.logbook_id)
                filename_gen = "CTCA_{0}_Logbook.xls".format(logbook_type[0].key())
                self.exportExcel(logbook_type[0].key())
                self.result = {"fulfillmentText":"<a href='{3}/downloadExcel/{0}' download={1}>{2}</a>".format(filename_unq,filename_gen,filename_gen,self.NAT)}
            else:
                for i in range(len(logbook_type)-1):
                    logbooks += logbook_type[i].key() + ', '
                logbooks += logbook_type[-1].key()
                self.result = {"fulfillmentText": "I note that you have <strong>{0}</strong> logbooks in our system, can you tell me which one you want to export".format(logbooks)}
     
        #==============logbook export==============
        if self.action == 'logbook_export':
            logbook_type = self.Training_Types if self.Training_Types else self.Training_Types_Re
            if '_' in logbook_type:
                recertf = logbook_type.split('_')[0]
                pathway = logbook_type.split('_')[1][-1]
                logbook_type = recertf.capitalize() +'_Pathway'+str(pathway)
            print('type is.   ',logbook_type)
            filename_unq = "CTCA_{0}_Logbook_{1}.xls".format(logbook_type,self.logbook_id)
            filename_gen = "CTCA_{0}_Logbook.xls".format(logbook_type)
            self.exportExcel(logbook_type)
            self.result = {"fulfillmentText":"<a href='{3}/downloadExcel/{0}' download={1}>{2}</a>".format(filename_unq,filename_gen,filename_gen,self.NAT)}
        #==============logbook find a sup ==============
        if self.action == 'logbook_sup_find':
            levelB = self.para.get('levelB')
            flag = False
            if not levelB:
                flag = True
                self.result = {"fulfillmentText": "Please tell me the CTCA training ID of the Level B specialist"}
            if not flag:
                ID = manager.db.child('Identification').child(levelB).get().val()
                if not ID:
                    self.result = {"fulfillmentText":"Sorry, the Level B specialist you are looking for does not exist."}
                elif levelB == self.ids:
                    self.result = {"fulfillmentText": "Sorry, your supervisor can not be yourself!"}
                else:
                    ID_level = manager.db.child('Identification').child(levelB).child('Identification').get().val()
                    levelBName = manager.db.child('User').child(levelB).child('User_name').get().val()
                    currentSup = manager.db.child('Trainee').child(self.ids).child('SupervisorUserID').get().val()
                    currentSupName = manager.db.child('User').child(currentSup).child('User_name').get().val()
                    if ID_level == 'B':
                        #put studnet ID under super student
                        if currentSup == "":
                            unverified_logs = manager.get_unverified_logbooks(self.ids)
                            unverified = ''
                            if not unverified_logs:
                                unverified = ''
                            elif len(unverified_logs)==1:
                                unverified = unverified_logs[0]
                            else:
                                unverified = ','.join(unverified_logs)
                            manager.db.child('Supervisor').child(levelB).child('Students').update({self.ids:unverified})
                            manager.db.child('Trainee').child(self.ids).update({'SupervisorUserID':levelB})
                            self.result = {"fulfillmentText": "Sure, I have informed your supervisor Dr."+levelBName}
                        else:
                            if levelBName == currentSupName:
                                self.result = {"fulfillmentText": "<strong>Dr.{0}".format(levelBName) + "</strong> is already your supervisor."}
                            else:
                                self.result = {"fulfillmentText": "Are you sure you want to change your supervisor from <strong>" + "Dr.{0}".format(currentSupName) + "</strong> to <strong>"+"Dr.{0}".format(levelBName)+"</strong>"}
                    else:
                        self.result = {"fulfillmentText": "Sorry, <strong>Dr.{0}".format(levelBName) + "</strong> is not a Level B specialist."}
        #==============logbook find a sup confirm==============
        if self.action == 'logbook_sup_find_confirm': 
            levelB = self.para.get('levelB')
            confirm = self.para.get('confirm')
            levelBName = manager.db.child('User').child(levelB).child('User_name').get().val()
            currentSup = manager.db.child('Trainee').child(self.ids).child('SupervisorUserID').get().val()
            if confirm == '1':
                stu_infor = manager.db.child('Supervisor').child(currentSup).child('Students').child(self.ids).get().val()
                manager.db.child('Supervisor').child(levelB).child('Students').update({self.ids:stu_infor})#update stu to new sup
                manager.db.child('Supervisor').child(currentSup).child('Students').child(self.ids).remove()#remove stu from old sup
                manager.db.child('Trainee').child(self.ids).update({'SupervisorUserID':levelB})#add sup to stu
                self.result = {"fulfillmentText":"Sure, I have informed your new supervisor <strong>Dr."+levelBName +"</strong>"}
            else:
                self.result = {"fulfillmentText": "Sure, I will not change your supervisor."}
        self.result = jsonify(self.result)
        return make_response(self.result)








