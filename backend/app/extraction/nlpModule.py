import nltk, re, pprint
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LTTextBoxHorizontal,LAParams
import nltk.classify.util
from nltk.corpus import movie_reviews
import pickle 

# This python file focus on creating module and save trained module.
# This python file will be run prior to the system starts.
# The classes in this file will be imported in other python files in order to load the trained module.
# The main() will not be run after the whole system starts and modules have been trained.
# We split provided sample reports to generate training data sat and train the model.
###################################################################################
def npchunk_features(sentence, i, history):# Feature extractor
		word, pos = sentence[i]
		if i == 0:
			prevword, prevpos = "<START>", "<START>"
		else:
			prevword, prevpos = sentence[i-1]
		#1 . Feature for the part-of-speech tag of the current token
		#2 . Feature for the previous part-of-speech tag
		#3 . Feature for the current word 
		return {"pos": pos, "word": word, "prevpos": prevpos}

class ConsecutiveNPChunkTagger(nltk.TaggerI):

    def __init__(self, train_sents):
        train_set = []
        for tagged_sent in train_sents:
            untagged_sent = nltk.tag.untag(tagged_sent)
            history = []
            for i, (word, tag) in enumerate(tagged_sent):
                featureset = npchunk_features(untagged_sent, i, history)
                train_set.append( (featureset, tag) )
                history.append(tag)
        # Use NaiveBayesClassifier in machine learning
        self.classifier = nltk.NaiveBayesClassifier.train(train_set)

    def tag(self, sentence):
        history = []
        for i, word in enumerate(sentence):
            featureset = npchunk_features(sentence, i, history)
            tag = self.classifier.classify(featureset)
            history.append(tag)
        # Create tragger
        return zip(sentence, history)
  
class ConsecutiveNPChunker(nltk.ChunkParserI):
    def __init__(self, train_sents):
        tagged_sents = [[((w,t),c) for (w,t,c) in nltk.chunk.tree2conlltags(sent)] for sent in train_sents]
        self.tagger = ConsecutiveNPChunkTagger(tagged_sents)

    # Convert the tag sequence into a chunk tree
    def parse(self, sentence):
        tagged_sents = self.tagger.tag(sentence)
        conlltags = [(w,t,c) for ((w,t),c) in tagged_sents]
        return nltk.chunk.conlltags2tree(conlltags)
###################################################################################
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
    for page in PDFPage.create_pages(doc):
        interpreter.process_page(page) 
        layout = device.get_result()
        ty = ''
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
################################################################################### 
# Chunking for "Date" item in schema
def get_date(list):
	traien = []
	grammar = r"""
		Date: {<NNP><VBD><.*><CD>}
		 	  {<VBD><IN><JJ>}
		 	  {<VBN><IN><NNP>+<.*>*<CD>}
	"""
	for i in list:
		doc = show_pag_tag('app/pdfs/https_page_{}.pdf'.format(i)) # /Users/congcong/Desktop/COMP9900/COMP9900_Project/capstone-project-gank/backend/app
		for te in doc:
			data = nltk.RegexpParser(grammar)
			result = data.parse(te)
			if len(nltk.chunk.tree2conlltags(result.subtrees(filter = lambda t : t.label() == 'Date'))) > 0:
				traien.append(result)
	# Return a list of a chunk tree
	return traien
################################################################################### 
# Chunking for "Facility" item in schema
def get_facility(list):
	traien = []
	grammar = r"""
		Facility: {<NNP>+<.*>?<NNP>+<.*>*<CC><NNP><.*>}
	"""
	for i in list:
		doc = show_pag_tag('app/pdfs/https_page_{}.pdf'.format(i))
		for te in doc:
			data = nltk.RegexpParser(grammar)
			result = data.parse(te)
			if len(nltk.chunk.tree2conlltags(result.subtrees(filter = lambda t : t.label() == 'Facility'))) > 0:
				traien.append(result)
	# Return a list of a chunk tree
	return traien

################################################################################### 
# Chunking for "DLP" item in schema
def get_dlp(list):
	traien = []
	grammar = r"""
		DLP: {<NNP><.*><CD>}
			 {<NNP><.*><.*><CD>}
			 {<NNP><VBD><CD><NNS>}
	"""
	for i in list:
		doc = show_pag_tag('app/pdfs/https_page_{}.pdf'.format(i))
		for te in doc:
			data = nltk.RegexpParser(grammar)
			result = data.parse(te)
			if len(nltk.chunk.tree2conlltags(result.subtrees(filter = lambda t : t.label() == 'DLP'))) > 0:
				traien.append(result)
	# Return a list of a chunk tree
	return traien
################################################################################### 
# Chunking for "ID" item in schema
def get_ID(list):
	traien = []
	grammar = r"""
		ID: {<JJ><NN.*><.*>?<CD>}
			{<.*>?<NN><.*>?<CD>}
			{<NNP><NNP><.*>?<CD>}
	"""
	for i in list:
		doc = show_pag_tag('app/pdfs/https_page_{}.pdf'.format(i))
		for te in doc:
			data = nltk.RegexpParser(grammar)
			result = data.parse(te)
			if len(nltk.chunk.tree2conlltags(result.subtrees(filter = lambda t : t.label() == 'ID'))) > 0:
				traien.append(result)
	# Return a list of a chunk tree
	return traien
################################################################################### 
# Chunking for "Dr" item in schema
def get_Dr(list):
	traien = []
	grammar = r"""
		DR: {<VBN|NN><IN><.*>?<NNP>+}
			{<NNP><NNP><.*>?<NNP>+}
	"""
	for i in list:
		doc = show_pag_tag('app/pdfs/https_page_{}.pdf'.format(i))
		for te in doc:
			data = nltk.RegexpParser(grammar)
			result = data.parse(te)
			if len(nltk.chunk.tree2conlltags(result.subtrees(filter = lambda t : t.label() == 'DR'))) > 0:
				traien.append(result)
	# Return a list of a chunk tree
	return traien

################################################################################### main module 
# Main module of machine learning
def main():
	# Create training data set basing on provided reports
	foot = [1,7,9,11,13,15,17,19,21,23,26,28,30,38,42,43,45,46,48,50,53,54,56,57]
	#nCreate training data set for doctor extraction basing on provided reports
	fot = [2,4,6,8,10,12,14,16,18,20,22,24,27,29,44,47,49,51,55,58]
	traien_date = get_date(foot)
	traien_facility = get_facility(foot)
	traien_dlp = get_dlp(foot)
	traien_ID = get_ID(foot)
	traien_Dr = get_Dr(fot)

	# Creaate tragger from classifier.
	unigram_chunker_date = ConsecutiveNPChunker(traien_date)
	unigram_chunker_facility = ConsecutiveNPChunker(traien_facility)
	unigram_chunker_dlp = ConsecutiveNPChunker(traien_dlp)
	unigram_chunker_ID = ConsecutiveNPChunker(traien_ID)
	unigram_chunker_Dr = ConsecutiveNPChunker(traien_Dr)

	# Save trained module to specific path in order to call the modules in operation.
	save_date = open('app/extraction/date.pickle','wb')
	pickle.dump(unigram_chunker_date,save_date)
	save_date.close()

	save_facility = open('app/extraction/facility.pickle','wb')
	pickle.dump(unigram_chunker_facility,save_facility)
	save_facility.close()

	save_dlp = open('app/extraction/DLP.pickle','wb')
	pickle.dump(unigram_chunker_dlp,save_dlp)
	save_dlp.close()

	save_ID = open('app/extraction/ID.pickle','wb')
	pickle.dump(unigram_chunker_ID,save_ID)
	save_ID.close()

	save_Dr = open('app/extraction/Dr.pickle','wb')
	pickle.dump(unigram_chunker_Dr,save_Dr)
	save_Dr.close()
	return 
# main() will be run to produce modules.
# if __name__ == '__main__':
# 	main()
























