#!/usr/bin/python
"""
    Backend application for CT Coronary Angiography (CTCA) Specialists logbook management Assistant.
    Official website: http://www.anzctca.org.au

"""
import os
from app import application
#, step1, step_2
from app.extraction.nlpModule import ConsecutiveNPChunkTagger, ConsecutiveNPChunker
# # from step1 import ConsecutiveNPChunkTagger, ConsecutiveNPChunker


# # ConsecutiveNPChunkTagger = step1.ConsecutiveNPChunkTagger
# # ConsecutiveNPChunker = step1.ConsecutiveNPChunker

if __name__ == '__main__':
    application.secret_key = os.urandom(12)
    application.run(debug=True)
