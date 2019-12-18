import nltk, re
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LTTextBoxHorizontal,LAParams
import nltk.classify.util
from nltk.corpus import movie_reviews, stopwords
import numpy as np
import pandas as pd


# Read content from training document.
def document(route):
    pdf0 = open(route,'rb')
    parser = PDFParser(pdf0)
    doc = PDFDocument(parser)
    parser.set_document(doc) 
    resources = PDFResourceManager()
    laparam = LAParams() 
    device = PDFPageAggregator(resources,laparams=laparam)
    interpreter = PDFPageInterpreter(resources,device)
    # print(doc.get_pages())
    d = {}
    f = []
    count = 1
    ty = ''
    for page in PDFPage.create_pages(doc):
        interpreter.process_page(page) 
        layout = device.get_result()
        for out in layout: 
            if hasattr(out,'get_text'):
                ty += out.get_text()
    return ty

def ie_preprocess(document):
	sentences = nltk.sent_tokenize(document)
	return sentences

def show_pag_tag(route):
	return ie_preprocess(document(route))

stop_words = stopwords.words('english')
word_embeding = {}
f = open('./backend/app/training_requirements/glove.6B.100d.txt', encoding = 'utf-8')#.
for line in f:
	values = line.split()
	word = values[0]
	coefs = np.asarray(values[1:],dtype = 'float32')
	word_embeding[word] = coefs
f.close()

def removw_stopwords(sen):
		sen_new = " ".join([i for i in sen if i not in stop_words])

		return sen_new

def get_textrank(list,dict):


	clean_sentences = pd.Series(list).str.replace("[^a-zA-z\/\(\)]"," ")
	clean_sentences = [s.lower() for s in clean_sentences]

	clean_sentences = [removw_stopwords(r.split()) for r in clean_sentences]

	sentences_vector = []
	for i in clean_sentences:
		if len(i) != 0:
			v= sum([dict.get(w,np.zeros((100,))) for w in i.split()])/(len(i.split())+0.001)
		else:
			v = np.zeros((100,))
		sentences_vector.append(v)
	sim_matrix = np.zeros([len(list),len(list)])

	from sklearn.metrics.pairwise import cosine_similarity

	for i in range(len(list)):
		for j in range(len(list)):
			if i != j:
				sim_matrix[i][j] = cosine_similarity(sentences_vector[i].reshape(1,100),sentences_vector[j].reshape(1,100))[0,0]


	import networkx as nx 

	nx_graph = nx.from_numpy_array(sim_matrix)
	scores = nx.pagerank(nx_graph)

	ranked_sentences = sorted(((scores[i],s) for i,s in enumerate(list)), reverse = True)

	return ranked_sentences

# Extract target sentences from text.
# Postprocesing on sentences.

dic_pre = {}
dic_train = {}
dic_recert = {}
dic_sub = {}
dic_con = {}
def get_prerequistie(dic_pre):
	dic_pre['prerequisite'] = []
	doc_1 = show_pag_tag('./backend/app/training_requirements/Training_Requirements_for_CTCA_Specialists_page_5.pdf')
	doc_2 = show_pag_tag('./backend/app/training_requirements/Training_Requirements_for_CTCA_Specialists_page_6.pdf')
	ranked_doc_1 = get_textrank(doc_1,word_embeding)[10:16]
	ranked_doc_2 = get_textrank(doc_2,word_embeding)[2:9]
	for i in range(len(ranked_doc_1)):
		if re.match(r"[Pp][Rr][Ee][Rr][Ee][Qq][Uu][Ii][Ss][Ii][Tt][Ee]",ranked_doc_1[i][1]):
			r = re.sub("[^a-zA-z\/\(\)\+\-\s]",'',ranked_doc_1[i][1]).split('Cardiologists')
			dic_pre['prerequisite'] = r
			dic_pre['Cardiologists'] = ['Cardiologists\n']
		if re.match(r"[Ee][Vv][Ii][Dd][Ee][Nn][Cc][Ee]",ranked_doc_1[i][1]):
			if re.match(r".*\;",ranked_doc_1[i][1]):
				r = re.findall(r".*\)",ranked_doc_1[i][1])[0]
				dic_pre['Cardiologists'].append(r)
			else:
				dic_pre['Cardiologists'].append(ranked_doc_1[i][1])
	for i in range(1,len(dic_pre['Cardiologists'])):
		dic_pre['Cardiologists'][i] = '{} '.format(i)+dic_pre['Cardiologists'][i]
	dic_pre['Cardiologists'].append('\n')
	for i in ranked_doc_2:
		if re.match(r"^\d",i[1]):
			er = re.findall(r"[^\d.\d\s].*\:",i[1])[0].split(':')[0]
			if er == 'Nuclear Medicine Physicians':
				dic_pre['Nuclear Medicine Physicians'] = ['Nuclear Medicine Physicians\n']
			if er == 'Radiologists':
				dic_pre['Radiologists'] = ['Radiologists\n']
	for j in range(len(ranked_doc_2)):
		if 'copy ' in ranked_doc_2[j][1]:
			if re.findall(r"\;\sOR",ranked_doc_2[j][1]):
				dic_pre['Nuclear Medicine Physicians'].append(('').join(ranked_doc_2[j][1].split(';')[0].split('\n')))
			else:
				dic_pre['Nuclear Medicine Physicians'].append(ranked_doc_2[j][1])
		elif re.match(r"^\d",ranked_doc_2[j][1]):
			continue
		else:
			if re.findall(r"\;\sOR",ranked_doc_2[j][1]):
				dic_pre['Radiologists'].append(ranked_doc_2[j][1].split(';')[0])
			else:
				dic_pre['Radiologists'].append(re.sub("[^a-zA-z\/\(\)\+\-\s]",'',ranked_doc_2[j][1]).split('\n')[0])
	for i in range(1,len(dic_pre['Nuclear Medicine Physicians'])):
		dic_pre['Nuclear Medicine Physicians'][i] = '{} '.format(i)+dic_pre['Nuclear Medicine Physicians'][i]
	dic_pre['Nuclear Medicine Physicians'].append('\n')
	for i in range(1,len(dic_pre['Radiologists'])):
		dic_pre['Radiologists'][i] = '{} '.format(i)+dic_pre['Radiologists'][i]
	dic_pre['Radiologists'].append('\n')
	return dic_pre
def get_training(dic_train):
	dic_train['training'] = []
	doc_2 = show_pag_tag('./backend/app/training_requirements/Training_Requirements_for_CTCA_Specialists_page_6.pdf')
	doc_3 = show_pag_tag('./backend/app/training_requirements/Training_Requirements_for_CTCA_Specialists_page_7.pdf')
	ranked_doc_2 = get_textrank(doc_2,word_embeding)[:2]
	ranked_doc_3 = get_textrank(doc_3,word_embeding)
	for i in ranked_doc_2:
		if re.findall(r"\;",i[1]):
			ee = i[1].split(';')[0]
		else:
			ee = i[1]
		ee =re.sub("\n\uf0b7",'',ee)
		ee = ('\n').join(re.findall(r"[^\d.\d\s].*",ee))
		r = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ee)
		dic_train['training'].append(r)
	p = dic_train['training'].pop()
	dic_train['levelA'] = []
	dic_train['levelA'].append(p)
	r = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_3[7][1])
	dic_train['levelA'].append(r)
	r = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_3[1][1])
	dic_train['levelA'].append('  '+r)

	dic_train['LevelB'] = []
	er = re.findall(r"[^\d.\d\s].*",ranked_doc_3[12][1])[0]
	dic_train['LevelB'].append(er)
	er = 'A. '+re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_3[2][1])
	dic_train['LevelB'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_3[0][1])
	dic_train['LevelB'].append(er)

	dic_train['LevelB_supervision'] = []
	er = ('\n').join(re.findall(r"[^\d.\d\s].*",ranked_doc_3[5][1]))
	dic_train['LevelB_supervision'].append(er)
	dic_train['LevelB_supervision'].append(ranked_doc_3[8][1])

	dic_train['training'].append('\n')
	dic_train['levelA'].append('\n')
	dic_train['LevelB'].append('\n')
	dic_train['LevelB_supervision'].append('\n')

	return dic_train

def get_recertification(dic_recert):
	dic_recert['recertification'] = []
	doc_3 = show_pag_tag('./backend/app/training_requirements/Training_Requirements_for_CTCA_Specialists_page_7.pdf')
	ranked_doc_3 = get_textrank(doc_3,word_embeding)
	doc_4 = show_pag_tag('./backend/app/training_requirements/Training_Requirements_for_CTCA_Specialists_page_8.pdf')
	ranked_doc_4 = get_textrank(doc_4,word_embeding)
	doc_5 = show_pag_tag('./backend/app/training_requirements/Training_Requirements_for_CTCA_Specialists_page_9.pdf')
	ranked_doc_5 = get_textrank(doc_5,word_embeding)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s]",'',ranked_doc_3[3][1])
	dic_recert['recertification'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',('\n').join(re.findall(r"[^\d.\d\s].*",ranked_doc_3[4][1])))
	dic_recert['recertification'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_3[6][1])
	dic_recert['recertification'].append(er)

	dic_recert['LevelB'] = []
	er = ('\n').join(re.findall(r"[^\d.\d\s].*",ranked_doc_4[1][1]))
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',er)
	dic_recert['LevelB'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_4[2][1])
	dic_recert['LevelB'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s]",'',ranked_doc_4[4][1])
	dic_recert['LevelB'].append(er)

	dic_recert['PATH1'] = []
	er = ('\n').join(re.findall(r"[^\d.\d\s].*",ranked_doc_4[17][1]))
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',er)
	dic_recert['PATH1'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_4[16][1])
	dic_recert['PATH1'].append(er)

	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_4[3][1])
	dic_recert['PATH1'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_4[5][1])
	dic_recert['PATH1'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_4[8][1])
	dic_recert['PATH1'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_4[10][1])
	dic_recert['PATH1'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_4[15][1])
	dic_recert['PATH1'].append(er)

	dic_recert['PATH2'] = []
	er = ('\n').join(re.findall(r"[^\d.\d\s].*",ranked_doc_4[7][1]))
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',er)
	dic_recert['PATH2'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_4[14][1])
	dic_recert['PATH2'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_4[6][1])
	dic_recert['PATH2'].append(er)
	
	
	dic_recert['PATH2 LevelB'] = []
	er = ('\n').join(re.findall(r"[^\d.\d\s].*",ranked_doc_5[2][1]))
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',('\n').join(er.split('\n')[2:]))
	dic_recert['PATH2 LevelB'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_5[14][1])
	dic_recert['PATH2 LevelB'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_5[7][1])
	dic_recert['PATH2 LevelB'].append(er)

	dic_recert['PATH2 Requirement'] = []
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_5[0][1])
	er = ('\n').join(er.split('\n')[1:])
	dic_recert['PATH2 Requirement'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',('\n').join(ranked_doc_5[2][1].split('\n')[:2]))
	dic_recert['PATH2 Requirement'].append(er)

	dic_recert['PATH2 logbook'] = []
	er = ('\n').join(re.findall(r"[^\d.\d\s].*",ranked_doc_5[1][1]))

	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',('\n').join(er.split('\n')[2:]))
	dic_recert['PATH2 logbook'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_5[3][1])
	dic_recert['PATH2 logbook'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_5[4][1])
	dic_recert['PATH2 logbook'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_5[9][1])
	dic_recert['PATH2 logbook'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_5[5][1])
	dic_recert['PATH2 logbook'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_5[10][1])
	dic_recert['PATH2 logbook'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_5[16][1])
	dic_recert['PATH2 logbook'].append(er)
	return dic_recert



def get_conversion(dic_con):
	dic_con['Conversion'] = []
	doc_6 = show_pag_tag('./backend/app/training_requirements/CCRTCTCA_Guideline for Conversion from Level A to Level B Registration_V4 2015_page_1.pdf')
	ranked_doc_6 = get_textrank(doc_6,word_embeding)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\:]",'',ranked_doc_6[1][1])
	dic_con['Conversion'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\;]",'',ranked_doc_6[7][1]).split(';')[0]
	dic_con['Conversion'].append(er)
	er =ranked_doc_6[3][1]
	dic_con['Conversion'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_6[0][1])+re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_6[9][1])
	dic_con['Conversion'].append(er)
	er = re.sub("[^a-zA-z\/\(\)\+\-\s\d]",'',ranked_doc_6[2][1])
	dic_con['Conversion'].append(er)
	return dic_con


def get_submission(dic_sub):
	dic_sub['Submission'] = []
	doc_3 = show_pag_tag('./backend/app/training_requirements/Training_Requirements_for_CTCA_Specialists_page_7.pdf')
	ranked_doc_3 = get_textrank(doc_3,word_embeding)
	dic_sub['Submission'].append(ranked_doc_3[14][1])
	dic_sub['Submission'].append(ranked_doc_3[9][1])

	return dic_sub

# Extract target sentences.
# Store sentences into a dictionary and save the dict as a .json file.
def main(dic_pre,dic_train,dic_recert,dic_sub,dic_con):
	pre = get_prerequistie(dic_pre)
	train = get_training(dic_train)
	recert = get_recertification(dic_recert)
	sub = get_submission(dic_sub)
	con = get_conversion(dic_con)
	return pre,train,recert,sub,con




