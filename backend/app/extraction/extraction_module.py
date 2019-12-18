#!/usr/bin/python

""" 
    CT Coronary Angiography (CTCA) Specialists training requirement and logbook extraction module.
    It access the official website and fetch the training requirements from the pdf file and download the logbook templates.
    Official website: http://www.anzctca.org.au
"""

import requests, re, os
from bs4 import BeautifulSoup
from PyPDF2 import PdfFileReader
from io import BytesIO

class ExtractionModule:
    """
        Arguments: 
            has_files:  Whether the pdf and logbook files existed in directory. 
            verbose:    Set true to print out extra info.
            writefiles: Allow to write extracted requirements to txt files.
    """
    def __init__(self, has_files=False, verbose=False, writefiles=False):

        self.ctca_url   = 'http://www.anzctca.org.au'
        self.sub_dir    = '/test'
        self.articleBody = None
        self.pdf_link   = None
        self.train_req  = ''    # training certification requirements
        self.recerti    = ''    # recertification requirements
        self.pdf_name   = 'Training_Requirements_for_CTCA_Specialists.pdf'
        self.lb1_name   = 'logbook_certification_training_template.xls'
        self.lb2_name   = 'logbook_recertification_training_pathway_1_template.xls'
        self.lb3_name   = 'logbook_recertification_training_pathway_2_template.xls'
        self.lb4_name   = 'logbook_conversion_template.xls'

        self.has_files  = has_files
        self.verbose    = verbose
        self.writefiles = writefiles


    def start(self):
        print('[INFO] Extraction module started.')
        if self.has_files:
            # Just access the files directly [?]
            self.__extract_pdf()
        else:
            self.__get_pdf()
            self.__extract_pdf()
            
        self.__get_logbooks()
        print('[INFO] Extraction module finished.')

    def __access(self, link):
        response = requests.get(link)
        if response.status_code != 200:
            raise ValueError(f'[ERROR] Cannot access the link! Please check if link is valid: {link}')
        else:
            return response.content

    def __get_pdf(self):
        if self.verbose:
            print(f'[INFO] Searching for training requirements on {self.ctca_url + self.sub_dir}')

        webpage = self.__access(self.ctca_url + self.sub_dir)
        soup = BeautifulSoup(webpage, 'html.parser')

        # Grab the training requirement pdf link
        self.articleBody = soup.find('div', {'itemprop':"articleBody"})
        # If webpage is consistant and not going to change dramatically:
        self.pdf_link = self.articleBody.ul.find(href=re.compile("[tT]raining.*[rR]equirements")).get('href')
        # Otherwise look for the pdf link:
        # links = self.articleBody.ul.findAll('li')
        # for i, txt in enumerate(links):
        #     if txt.text == 'Training Requirements':
        #         self.pdf_link = txt.a.get('href')
        #         break
        # print(self.pdf_link)
        
        # Download the pdf from the link
        buffer = self.__access(self.ctca_url + self.pdf_link)
        if self.verbose:
            print(f'[INFO] Found the pdf file. Downloading...')
        # pdf_stream = BytesIO(buffer)
        with open(self.pdf_name, 'wb') as f:
            f.write(buffer)
        print(f'[DONE] Training requirement saved as {self.pdf_name}')


    def __extract_pdf(self):

        """ Read local pdf file and extract information. """

        # if self.has_files:
        if not os.path.exists(self.pdf_name):
            print('[WARN] pdf file does not exist! Redownloading..')
            self.__get_pdf()

        if self.verbose:
            print(f'[INFO] Reading pdf file {self.pdf_name}')
        with open(self.pdf_name, 'rb') as pdf_stream:
            pdf = PdfFileReader(pdf_stream)
            # Extract the content and filter out the part we need
            contents = ''
            for page in range(1, pdf.getNumPages()-1):
                tmp = pdf.getPage(page).extractText()
                contents += tmp
            if self.verbose:
                print(f'[INFO] Contents from the pdf file extracted. (Ignored first and last pages)')

        interest = contents.split('TRAINING REQUIREMENTS')[-1]
        interest = interest.split('APPLICATION PROCESS')[0]
        interest = interest.split('RECERTIFICATION OF REGISTRATION')
        self.train_req = interest[0]
        self.recerti = interest[-1]
        if self.verbose:
            print(f'[INFO] Extracted certification and recertification requirements.')

        if self.writefiles:
            # print(contents)
            with open('train_requirements.txt', 'w', encoding='utf-8') as f:
                f.write(self.train_req)
            with open('recertification.txt', 'w', encoding='utf-8') as f:
                f.write(self.recerti)
            if self.verbose:
                print(f"[DONE] Requirements saved as 'train_requirements.txt' and 'recertification.txt' ")


    def __get_logbooks(self):

        # 1. Logbook for CTCA specialist certification
        if self.verbose:
            print(f'[INFO] Searching for logbook templates for certification on {self.ctca_url + self.sub_dir}')
        assert (self.articleBody is not None), '[ERROR] URL invalid!'
        lb1_link = self.articleBody.ul.find(href=re.compile("[^eE][cC]ertification.*[lL]ogbook.*[tT]emplate")).get('href')
        # print(lb1_link)

        # Fetch the logbook and write to .xls file
        buffer = self.__access(self.ctca_url + lb1_link)
        with open(self.lb1_name, 'wb') as f:
            f.write(buffer)
        if self.verbose:
            print(f'[DONE] Logbook templates for certification saved as {self.lb1_name}')


        # Find links to recertification and conversion webpage
        recert_link = ''
        conversion_link = ''
        links = self.articleBody.findAll('a')
        for txt in links:
            try:
                if re.search("[rR]ecertification", txt.text) is not None:
                    recert_link = txt.get('href')
                if re.search("[cC]onversion", txt.text) is not None:
                    conversion_link = txt.get('href')
            except ValueError:
                pass

        if recert_link == '' or conversion_link == '':
            raise ValueError(f'[ERROR] Cannot find the recerti/conversion link! Please check if website changed.')
        elif self.verbose:
            print(f'[INFO] Found links to recerti/conversion pages.')


        # 2. Logbook for CTCA specialist recertification (pathway 1 and 2)
        if self.verbose:
            print(f'[INFO] Searching for logbook templates for recertification on {self.ctca_url + recert_link}')
        # Access the webpage
        webpage = self.__access(self.ctca_url + recert_link)
        soup = BeautifulSoup(webpage, 'html.parser')
        articleBody = soup.find('div', {'itemprop':"articleBody"})

        # Find links to recertification logbook templates for both pathways
        links = articleBody.findAll('a')
        for txt in links:
            try:
                if re.search("[lL]ogbook.*[pP]athway.*1", txt.text) is not None:
                    path_1_link = txt.get('href')
                if re.search("[lL]ogbook.*[pP]athway.*2", txt.text) is not None:
                    path_2_link = txt.get('href')
            except ValueError:
                pass

        buffer = self.__access(self.ctca_url + path_1_link)
        with open(self.lb2_name, 'wb') as f:
            f.write(buffer)
        if self.verbose:
            print(f'[DONE] Logbook templates for recertification pathway 1 saved as {self.lb2_name}')

        buffer = self.__access(self.ctca_url + path_2_link)
        with open(self.lb3_name, 'wb') as f:
            f.write(buffer)
        if self.verbose:
            print(f'[DONE] Logbook templates for recertification pathway 2 saved as {self.lb3_name}')


        # 3. Logbook for conversion from level A to B CTCA specialist 
        if self.verbose:
            print(f'[INFO] Searching for logbook templates for level conversion on {self.ctca_url + conversion_link}')
        # Access the webpage
        webpage = self.__access(self.ctca_url + conversion_link)
        soup = BeautifulSoup(webpage, 'html.parser')
        articleBody = soup.find('div', {'itemprop':"articleBody"})

        links = articleBody.findAll('a')
        for txt in links:
            try:
                if re.search("[lL]ogbook.*[cC]onversion", txt.text) is not None:
                    conv_link = txt.get('href')
            except ValueError:
                pass
                
        buffer = self.__access(self.ctca_url + conv_link)
        with open(self.lb4_name, 'wb') as f:
            f.write(buffer)
        if self.verbose:
            print(f'[DONE] Logbook templates for certification saved as {self.lb4_name}')


if __name__ == "__main__":
    ll = ExtractionModule(has_files = 0, verbose=True, writefiles=True)
    ll.start()











