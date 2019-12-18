import os
import re
import xlrd
from os import path
from os.path import dirname, abspath

# Extract required schema from logbook templates.
def skeletonize(str):
	item = str
	keys_1 = ['Supervising']
	keys_2 = ['U','E','N']
	keys_3 = ['OR','Patient','ID']
	keys_4 = ['Co','reporting']
	total_length = len(item)
	result, next_match_index, skip = '', -1, 0

	for i in range(total_length):
		if skip:
			skip -= 1
			continue
		for key1 in keys_1:
			length = len(key1)

			if i+length <= total_length:
				s = str[i:i + length]
				if s == key1:
					split = '' if next_match_index == i else ''
					result = result + split + key1
					next_match_index = i+length
					skip = length - 1
					break

	if not result:
		for i in range(total_length):
			if skip:
				skip -= 1
				continue
			for key2 in keys_2:
				length = len(key2)

				if i+length <= total_length:
					s = str[i:i + length]
					if s == key2:
						split = '' if next_match_index == i else ' '
						result = result + split + key2
						next_match_index = i+length
						skip = length - 1
						break

		result = ''.join(result.split())
		for i in range(total_length):
			if skip:
				skip -= 1
				continue
			for key3 in keys_3:
				length = len(key3)

				if i+length <= total_length:
					s = str[i:i + length]
					if s == key3:
						split = '' if next_match_index == i else ' '
						result = result + split + key3
						next_match_index = i+length
						skip = length - 1
						break
		result = '_'.join(result.split())
	if not result:
		for i in range(total_length):
			if skip:
				skip -= 1
				continue
			for key4 in keys_4:
				length = len(key4)

				if i+length <= total_length:
					s = str[i:i + length]
					if s == key4:
						split = '' if next_match_index == i else ' '
						result = result + split + key4
						next_match_index = i+length
						skip = length - 1
						break
		result = '_'.join(result.split())
	return result

# Please change the path to your surrent path fo logbook templates.
def logbook_entry(logbook_type,path_way=False):
	dic = {}
	file_url =dirname(abspath(__file__))+'/'
	files = os.listdir(file_url)
	xls_files = [f for f in files if re.match(r".*.xls$",f)]
	file_name = ''
	ll = logbook_type
	if ll == 'certification':
		for i in xls_files:
			if re.match(r".*_{}_".format(ll),i):
				file_name = i
				print(file_name)
		data = xlrd.open_workbook(file_url+file_name)
		rr = data.sheet_names()
		for r in rr:
			if re.match(r"[Ll]ogbook",r):
				sheet_name = r
				break 
		table = data.sheet_by_name(sheet_name)
		bb = table.row_values(0)
		dd = table.row_values(2)
		for h in bb:
			if h != '' :
				if 'Exam' in h:
					continue
				if 'Case type' in h:
					continue
				he = '_'.join(h.split())
				if re.match(r".*#$", he):
					he = he[:-2]
				if len(he) >= 30:
					he = skeletonize(he)
				dic[he] = ''
		for k in dd:
			if k != '' :
				if 'DLP' in k:
					k = 'DLP'
				if 'Case from CT course' in k:
					k = 'Case from CT course'
				ke = '_'.join(k.split())
				if re.match(r".*#$", ke):
					ke = ke[:-2]
				if len(ke) >= 30:
					ke = skeletonize(ke)
				dic[ke] = ''

	elif ll == 'conversion':
		for i in xls_files:
			if re.match(r".*_{}_".format(ll),i):
				file_name = i
		data = xlrd.open_workbook(file_url+file_name)
		rr = data.sheet_names()
		for r in rr:
			if re.match(r"[Ll]ogbook",r):
				sheet_name = r
				break 
		table = data.sheet_by_name(sheet_name)
		bb = table.row_values(0)

		dd = table.row_values(2)

		for h in bb:
			if h != '' :
				if 'Exam' in h:
					continue
				if 'Case type' in h:
					continue
				he = '_'.join(h.split())
				if re.match(r".*#$", he):
					he = he[:-2]
				if len(he) >= 30:
					he = skeletonize(he)
				dic[he] = ''
		for k in dd:
			if k != '' :
				if 'Thoracic Aorta' in k:
					k = 'Graft Or Thoracic Aorta'
				ke = '_'.join(k.split())
				if re.match(r".*#$", ke):
					ke = ke[:-2]
				if len(ke) >= 30:
					ke = skeletonize(ke)
				dic[ke] = ''

	elif ll == 'recertification':
		yy = path_way
		for i in xls_files:
			if re.match(r".*_{}_.*_pathway_{}".format(ll,yy),i):
				file_name = i
		data = xlrd.open_workbook(file_url+file_name)
		rr = data.sheet_names()
		for r in rr:
			if re.match(r"[Ll]ogbook",r):
				sheet_name = r
				break 
		table = data.sheet_by_name(sheet_name)
		bb = table.row_values(0)

		dd = table.row_values(2)

		for h in bb:
			if h != '' :
				if 'Exam' in h:
					continue
				if 'Case type' in h:
					continue
				he = '_'.join(h.split())
				if re.match(r".*#$", he):
					he = he[:-2]
				if len(he) >= 30:
					he = skeletonize(he)
				dic[he] = ''
		for k in dd:
			if k != '' :
				if 'Thoracic Aorta' in k:
					k = 'Graft Or Thoracic Aorta'
				ke = '_'.join(k.split())
				if re.match(r".*#$", ke):
					ke = ke[:-2]
				if len(ke) >= 30:
					ke = skeletonize(ke)
				dic[ke] = ''
	return dic
