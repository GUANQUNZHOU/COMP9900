import nltk, re, pprint
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LTTextBoxHorizontal,LAParams
import nltk.classify.util
from nltk.corpus import movie_reviews
from app.extraction.nlpModule import ConsecutiveNPChunkTagger,ConsecutiveNPChunker
import pickle

# Since some information like name of doctor has been hidden bacause of security reason.
# In the main class there are to operation function.
# And one of the functions will be executed according to if uploaded report is a sample report.
# Extract all of target information from uploaded report.
# Create linked list
class Link:
    empty = ()
    def __init__(self, first, rest=empty):
        assert rest is Link.empty or isinstance(rest, Link)
        self.first = first
        self.rest = rest

def list_to_link(lst):
    if len(lst) == 1:
        return Link(lst[0])
    return Link(lst[0], list_to_link(lst[1:]))
# Read content from uploaded report(Read text from pdf files)
def document(route):
    parser = PDFParser(route)
    doc = PDFDocument(parser)
    parser.set_document(doc) 
    resources = PDFResourceManager()
    laparam = LAParams() 
    device = PDFPageAggregator(resources,laparams=laparam)
    interpreter = PDFPageInterpreter(resources,device)
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
    # Return a String Object whose content is the content of report
    return ty

def ie_preprocess(document):
	# Sentence segmenation
	sentences = nltk.sent_tokenize(document)
	# tokenization
	sentences = [nltk.word_tokenize(sent) for sent in sentences]
	# complete part-of-speech tagging
	sentences = [nltk.pos_tag(sent) for sent in sentences]
	return sentences

def show_pag_tag(route):
	return ie_preprocess(document(route))

# Class for schema extraction from uploaded reports
class main_processing():
	# Arguments:
	# route: bytes object of uploaded report
	# sample: indicate if uploaded report is a sample report.
	def __init__(self, route, sample = True):
		self.route = route
		self.sample = sample

	# Load pickle files which are modules provided by nlpOperation.py
	def sample_operation(self):
		t2 = show_pag_tag(self.route)
		load_date = open('app/extraction/date.pickle','rb')
		use_date = pickle.load(load_date)
		load_date.close()

		load_fac = open('app/extraction/facility.pickle','rb')
		use_fac = pickle.load(load_fac)
		load_fac.close()

		load_dlp = open('app/extraction/DLP.pickle','rb')
		use_dlp = pickle.load(load_dlp)
		load_dlp.close()

		load_ID= open('app/extraction/ID.pickle','rb')
		use_ID = pickle.load(load_ID)
		load_ID.close()

		load_Dr= open('app/extraction/Dr.pickle','rb')
		use_Dr = pickle.load(load_Dr)
		load_Dr.close()
###################################################################################
		# Initilize tratget variables
		flag = False
		target_date = []
		dlp_value = 0
		id_value = 0
		target_Dr = {}#1
		target_Dr['Supervisor'] = []
		target_Dr['Co-report'] = []
		cor = ''
		car = ''
		ty = document(self.route)
		for j in ty.split('\n'):
			if re.findall(r"[Aa][Dd][Dd][Ii][Tt][Ii][Oo][Nn][Aa][Ll].*[Cc][Aa][Rr][Dd][Ii][Aa][Cc].*[Ff][Ii][Nn][Dd][Ii][Nn][Gg][Ss]",j):
			                cor = '1'
			                car = '1'
			                break
			    
		for i in t2:
			# Generate target chunk trees
			tryy_date = use_date.parse(i)
			tryy_facility = use_fac.parse(i)
			tryy_dlp = use_dlp.parse(i)
			tryy_ID = use_ID.parse(i)
			tryy_Dr = use_Dr.parse(i)

			# Convert a Chunk tree into tag sequence.
			# Generate target tokens using linked list.
			# Postprecessing  on target tokens in order to extract target schema accurately.
			# Filter information using Regular Expression.
			if len(nltk.chunk.tree2conlltags(tryy_date.subtrees(filter = lambda t : t.label() == 'Date'))) > 2:
				link_date = list_to_link(nltk.chunk.tree2conlltags(tryy_date.subtrees(filter = lambda t : t.label() == 'Date')))
				s = link_date.first
				if link_date.rest:
					ss = link_date.rest
					sss = ss.first
					start = s[0]
					while ss.rest:
						start = start+' '+sss[0]
						ss = ss.rest
						sss = ss.first
					start = start+' '+sss[0]
				if re.findall(r"\d+[\-\/\.]\w*[\-\/\.]\d+",start):
					target_date.append(re.findall(r"\d+[\-\/\.]\w*[\-\/\.]\d+",start)[0]) 
			if len(nltk.chunk.tree2conlltags(tryy_facility.subtrees(filter = lambda t : t.label() == 'Facility'))) > 10:
				link_facility = list_to_link(nltk.chunk.tree2conlltags(tryy_facility.subtrees(filter = lambda t : t.label() == 'Facility')))
				s = link_facility.first
				ss = link_facility.rest
				sss = ss.first
				start = s[0]
				while sss[2] == 'I-Facility' and ss.rest:
					start = start+' '+sss[0]
					ss = ss.rest
					sss = ss.first
				start = start+' '+sss[0]
				if re.findall(r".*POWH.*",start):
					flag = True
			if len(nltk.chunk.tree2conlltags(tryy_dlp.subtrees(filter = lambda t : t.label() == 'DLP'))) > 0:
				link_dlp = list_to_link(nltk.chunk.tree2conlltags(tryy_dlp.subtrees(filter = lambda t : t.label() == 'DLP')))
				s = link_dlp.first
				if link_dlp.rest:
					ss = link_dlp.rest
					sss = ss.first
					start = s[0]
					while ss.rest:
						start = start+' '+sss[0]
						ss = ss.rest
						sss = ss.first
					start = start+' '+sss[0]
				else:
					start = s[0]
				if 'DLP' in start:
					search = start.split(' ')
					index = search.index('DLP')
					for i in range(index+1,len(search)):
						if re.findall(r"\d+",search[i]):
							dlp_value = eval(search[i])
							break
			if len(nltk.chunk.tree2conlltags(tryy_ID.subtrees(filter = lambda t : t.label() == 'ID'))) > 2:
				link_ID = list_to_link(nltk.chunk.tree2conlltags(tryy_ID.subtrees(filter = lambda t : t.label() == 'ID')))
				s = link_ID.first
				if link_ID.rest:
					ss = link_ID.rest
					sss = ss.first
					start = s[0]
					while ss.rest:
						start = start+' '+sss[0]
						ss = ss.rest
						sss = ss.first
					start = start+' '+sss[0]
				else:
					start = s[0]
				if 'Ward' in start:
					search = start.split(' ')
					index = search.index('Ward')
					for i in range(index+1,len(search)):
						if re.findall(r"\d+",search[i]):
							id_value = eval(search[i])
							break
				if 'Exam' in start and 'Date' in start:
					search = start.split(' ')
					index = search.index('Exam')
					for i in range(index+1,len(search)):
						if re.findall(r"\d+",search[i]):
							id_value = eval(search[i])
							break
				if 'Exam' in start:
					search = start.split(' ')
					index = search.index('Exam')
					for i in range(index+1,len(search)):
						if re.findall(r"\d+",search[i]):
							id_value = eval(search[i])
							break
				if '#' in start:
					search = start.split(' ')
					index = search.index('#')
					for i in range(index+1,len(search)):
						if re.findall(r"\d+",search[i]):
							id_value = eval(search[i])
							break

			if len(nltk.chunk.tree2conlltags(tryy_Dr.subtrees(filter = lambda t : t.label() == 'DR'))) > 2:
				ink_Dr = list_to_link(nltk.chunk.tree2conlltags(tryy_Dr.subtrees(filter = lambda t : t.label() == 'DR')))
				s = ink_Dr.first
				if ink_Dr.rest:
					ss = ink_Dr.rest
					sss = ss.first
					start = s[0]
					while ss.rest:
						start = start+' '+sss[0]
						ss = ss.rest
						sss = ss.first
					start = start+' '+sss[0]
				else:
					start = s[0]
				if 'Dr' in start or 'DR' in start:
					start = re.sub("[^a-zA-z\s]",' ',start)
					if re.match(r".*Approved.*",start):
						st = start.split('Approved')[-1]
						index = [i for (i,j) in enumerate(st.split(' ')) if j == 'Dr' or j == 'DR']
						n = index[0]
						name = st.split(' ')[n]+' '+st.split(' ')[n+1]+' '+st.split(' ')[n+2]
						if name not in target_Dr['Supervisor']:
							if len(target_Dr['Co-report']) > 0:
								if name in target_Dr['Co-report']:
									target_Dr['Co-report'].remove(name)
									target_Dr['Supervisor'].append(name)
							else:
								target_Dr['Supervisor'].append(name)
					elif re.match(r".*Authorised.*",start):
						st = start.split('Authorised')[-1]
						index = [i for (i,j) in enumerate(st.split(' ')) if j == 'Dr' or j == 'DR']
						n = index[0]
						name = st.split(' ')[n]+' '+st.split(' ')[n+1]+' '+st.split(' ')[n+2]
						if name not in target_Dr['Supervisor']:
							if len(target_Dr['Co-report']) > 0:
								if name in target_Dr['Co-report']:
									target_Dr['Co-report'].remove(name)
									target_Dr['Supervisor'].append(name)
							else:
								target_Dr['Supervisor'].append(name)
					elif re.match(r".*Supervised.*",start):
						st = start.split('Supervised')[-1]
						index = [i for (i,j) in enumerate(st.split(' ')) if j == 'Dr' or j == 'DR']
						n = index[0]
						name = st.split(' ')[n]+' '+st.split(' ')[n+1]+' '+st.split(' ')[n+2]
						if name not in target_Dr['Supervisor']:
							if len(target_Dr['Co-report']) > 0:
								if name in target_Dr['Co-report']:
									target_Dr['Co-report'].remove(name)
									target_Dr['Supervisor'].append(name)
							else:
								target_Dr['Supervisor'].append(name)
					index = [i for (i,j) in enumerate(start.split(' ')) if j == 'Dr' or j == 'DR']

					for n in index:
						name = start.split(' ')[n]+' '+start.split(' ')[n+1]+' '+start.split(' ')[n+2]
						if re.match(r".*[Ww][Oo][Rr][Kk]\s[Ss][Ii][Tt][Ee]",name):
							continue
						if 'Dr' in name:
							name_list = name.split(' ')
							name_list.remove('Dr')
							count = 0
							for i in name_list:
								if i != '':
									count+=1
							if count > 0:
								if name not in target_Dr['Supervisor'] and name not in target_Dr['Co-report']:
									target_Dr['Co-report'].append(name)
						if 'DR' in name:
							name_list = name.split(' ')
							name_list.remove('DR')
							count = 0
							for i in name_list:
								if i != '':
									count+=1
							if count > 0:
								if name not in target_Dr['Supervisor'] and name not in target_Dr['Co-report']:
									target_Dr['Co-report'].append(name)
		if flag:
			tartget_fac = 'Randwick Medical Imaging Department'
		if not flag:
			tartget_fac = 'Spectrum Randwick'
		return target_date,tartget_fac,dlp_value,id_value,target_Dr

	# Extract human name of the content of report and store human names in a list.
	# Extract human name using StanfordNERTagger
	def human_name(self):
		hn = []
		import nltk
		from nltk.tag import StanfordNERTagger
		stanford_ner_tagger = StanfordNERTagger(
	    'stanford_ner/' + 'classifiers/english.muc.7class.distsim.crf.ser.gz',
	    'stanford_ner/' + 'stanford-ner-3.9.2.jar')
		article = document(self.route)
		article = re.sub("[^a-zA-z\s]",' ',article)
		results = stanford_ner_tagger.tag(article.split(' '))
		for result in results:
		    tag_value = result[0]
		    tag_type = result[1]
		    if tag_type != 'O':
		    	if tag_type == 'PERSON' and tag_value not in hn:
		    		hn.append(tag_value)
		return hn
	# Operation for real reports
	def real_operation(self):
		hn = human_name(self)
		t2 = show_pag_tag(self.route)
		load_date = open('app/extraction/date.pickle','rb')
		use_date = pickle.load(load_date)
		load_date.close()

		load_fac = open('app/extraction/facility.pickle','rb')
		use_fac = pickle.load(load_fac)
		load_fac.close()

		load_dlp = open('app/extraction/DLP.pickle','rb')
		use_dlp = pickle.load(load_dlp)
		load_dlp.close()

		load_ID= open('app/extraction/ID.pickle','rb')
		use_ID = pickle.load(load_ID)
		load_ID.close()

		load_Dr= open('app/extraction/Dr.pickle','rb')
		use_Dr = pickle.load(load_Dr)
		load_Dr.close()
###################################################################################
		flag = False
		target_date = []
		dlp_value = 0
		id_value = 0
		target_Dr = {}#1
		target_Dr['Supervisor'] = []
		target_Dr['Co-report'] = []
		cor = ''
		car = ''
		ty = document(self.route)
		for j in ty.split('\n'):
			if re.findall(r"[Aa][Dd][Dd][Ii][Tt][Ii][Oo][Nn][Aa][Ll].*[Cc][Aa][Rr][Dd][Ii][Aa][Cc].*[Ff][Ii][Nn][Dd][Ii][Nn][Gg][Ss]",j):
			                cor = '1'
			                car = '1'
			                break
			    
		for i in t2:
			tryy_date = use_date.parse(i)
			tryy_facility = use_fac.parse(i)
			tryy_dlp = use_dlp.parse(i)
			tryy_ID = use_ID.parse(i)
			tryy_Dr = use_Dr.parse(i)

			if len(nltk.chunk.tree2conlltags(tryy_date.subtrees(filter = lambda t : t.label() == 'Date'))) > 2:
				link_date = list_to_link(nltk.chunk.tree2conlltags(tryy_date.subtrees(filter = lambda t : t.label() == 'Date')))
				s = link_date.first
				if link_date.rest:
					ss = link_date.rest
					sss = ss.first
					start = s[0]
					while ss.rest:
						start = start+' '+sss[0]
						ss = ss.rest
						sss = ss.first
					start = start+' '+sss[0]
				if re.findall(r"\d+[\-\/\.]\w*[\-\/\.]\d+",start):
					target_date.append(re.findall(r"\d+[\-\/\.]\w*[\-\/\.]\d+",start)[0]) 
			if len(nltk.chunk.tree2conlltags(tryy_facility.subtrees(filter = lambda t : t.label() == 'Facility'))) > 10:
				link_facility = list_to_link(nltk.chunk.tree2conlltags(tryy_facility.subtrees(filter = lambda t : t.label() == 'Facility')))
				s = link_facility.first
				ss = link_facility.rest
				sss = ss.first
				start = s[0]
				while sss[2] == 'I-Facility' and ss.rest:
					start = start+' '+sss[0]
					ss = ss.rest
					sss = ss.first
				start = start+' '+sss[0]
				if re.findall(r".*POWH.*",start):
					flag = True
			if len(nltk.chunk.tree2conlltags(tryy_dlp.subtrees(filter = lambda t : t.label() == 'DLP'))) > 0:
				link_dlp = list_to_link(nltk.chunk.tree2conlltags(tryy_dlp.subtrees(filter = lambda t : t.label() == 'DLP')))
				s = link_dlp.first
				if link_dlp.rest:
					ss = link_dlp.rest
					sss = ss.first
					start = s[0]
					while ss.rest:
						start = start+' '+sss[0]
						ss = ss.rest
						sss = ss.first
					start = start+' '+sss[0]
				else:
					start = s[0]
				if 'DLP' in start:
					search = start.split(' ')
					index = search.index('DLP')
					for i in range(index+1,len(search)):
						if re.findall(r"\d+",search[i]):
							dlp_value = eval(search[i])
							break
			if len(nltk.chunk.tree2conlltags(tryy_ID.subtrees(filter = lambda t : t.label() == 'ID'))) > 2:
				link_ID = list_to_link(nltk.chunk.tree2conlltags(tryy_ID.subtrees(filter = lambda t : t.label() == 'ID')))
				s = link_ID.first
				if link_ID.rest:
					ss = link_ID.rest
					sss = ss.first
					start = s[0]
					while ss.rest:
						start = start+' '+sss[0]
						ss = ss.rest
						sss = ss.first
					start = start+' '+sss[0]
				else:
					start = s[0]
				if 'Ward' in start:
					search = start.split(' ')
					index = search.index('Ward')
					for i in range(index+1,len(search)):
						if re.findall(r"\d+",search[i]):
							id_value = eval(search[i])
							break
				if 'Exam' in start and 'Date' in start:
					search = start.split(' ')
					index = search.index('Exam')
					for i in range(index+1,len(search)):
						if re.findall(r"\d+",search[i]):
							id_value = eval(search[i])
							break
				if 'Exam' in start:
					search = start.split(' ')
					index = search.index('Exam')
					for i in range(index+1,len(search)):
						if re.findall(r"\d+",search[i]):
							id_value = eval(search[i])
							break
				if '#' in start:
					search = start.split(' ')
					index = search.index('#')
					for i in range(index+1,len(search)):
						if re.findall(r"\d+",search[i]):
							id_value = eval(search[i])
							break

			if len(nltk.chunk.tree2conlltags(tryy_Dr.subtrees(filter = lambda t : t.label() == 'DR'))) > 2:
				ink_Dr = list_to_link(nltk.chunk.tree2conlltags(tryy_Dr.subtrees(filter = lambda t : t.label() == 'DR')))
				s = ink_Dr.first
				if ink_Dr.rest:
					ss = ink_Dr.rest
					sss = ss.first
					start = s[0]
					while ss.rest:
						start = start+' '+sss[0]
						ss = ss.rest
						sss = ss.first
					start = start+' '+sss[0]
				else:
					start = s[0]
				if 'Dr' in start or 'DR' in start:
					start = re.sub("[^a-zA-z\s]",' ',start)
					print(start)
					if re.match(r".*Approved.*",start):
						st = start.split('Approved')[-1]
						index = [i for (i,j) in enumerate(st.split(' ')) if j == 'Dr' or j == 'DR']
						n = index[0]
						SPc = 1
						while start.split(' ')[n+SPc] in hn:
							SPc += 1
						name = ' '.join(start.split(' ')[n:n+SPc])
						if name not in target_Dr['Supervisor']:
							if len(target_Dr['Co-report']) > 0:
								if name in target_Dr['Co-report']:
									target_Dr['Co-report'].remove(name)
									target_Dr['Supervisor'].append(name)
							else:
								target_Dr['Supervisor'].append(name)
					elif re.match(r".*Authorised.*",start):
						st = start.split('Authorised')[-1]
						index = [i for (i,j) in enumerate(st.split(' ')) if j == 'Dr' or j == 'DR']
						n = index[0]
						SPc = 1
						while start.split(' ')[n+SPc] in hn:
							SPc += 1
						name = ' '.join(start.split(' ')[n:n+SPc])
						if name not in target_Dr['Supervisor']:
							if len(target_Dr['Co-report']) > 0:
								if name in target_Dr['Co-report']:
									target_Dr['Co-report'].remove(name)
									target_Dr['Supervisor'].append(name)
							else:
								target_Dr['Supervisor'].append(name)
					elif re.match(r".*Supervised.*",start):
						st = start.split('Supervised')[-1]
						index = [i for (i,j) in enumerate(st.split(' ')) if j == 'Dr' or j == 'DR']
						n = index[0]
						SPc = 1
						while start.split(' ')[n+SPc] in hn:
							SPc += 1
						name = ' '.join(start.split(' ')[n:n+SPc])
						if name not in target_Dr['Supervisor']:
							if len(target_Dr['Co-report']) > 0:
								if name in target_Dr['Co-report']:
									target_Dr['Co-report'].remove(name)
									target_Dr['Supervisor'].append(name)
							else:
								target_Dr['Supervisor'].append(name)

					index = [i for (i,j) in enumerate(start.split(' ')) if j == 'Dr' or j == 'DR']

					for n in index:
						SPc = 1
						while start.split(' ')[n+SPc] in hn:
							SPc += 1
						name = ' '.join(start.split(' ')[n:n+SPc])
						if re.match(r".*[Ww][Oo][Rr][Kk]\s[Ss][Ii][Tt][Ee]",name):
							continue
						if 'Dr' in name:
							name_list = name.split(' ')
							name_list.remove('Dr')
							count = 0
							for i in name_list:
								if i != '':
									count+=1
							if count > 0:
								if name not in target_Dr['Supervisor'] and name not in target_Dr['Co-report']:
									target_Dr['Co-report'].append(name)
						if 'DR' in name:
							name_list = name.split(' ')
							name_list.remove('DR')
							count = 0
							for i in name_list:
								if i != '':
									count+=1
							if count > 0:
								if name not in target_Dr['Supervisor'] and name not in target_Dr['Co-report']:
									target_Dr['Co-report'].append(name)

		if flag:
			tartget_fac = 'Randwick Medical Imaging Department'
		if not flag:
			tartget_fac = 'Spectrum Randwick'
		return target_date,tartget_fac,dlp_value,id_value,target_Dr
	# According whether uploaded report is a sample report, execute expected function.
	def execute(self):
		if self.sample:
			return self.sample_operation()
		if not self.sample:
			return self.real_operation()