##############################################
#
#   Issue Management + Release Notes Generation
#   (Automatic Bug Triage and Assignment by Topic Modelling)
#   Draft only
#
#	Author:          Alex Poon
#	Date:            Sep 30, 2021
#	Last update:     Oct 9, 2021
#
##############################################

from glob import glob
from os.path import dirname, basename
from collections import Counter

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import guess_lexer, find_lexer_class_for_filename

import pygraphviz
'''
# for UML (?), download from https://www.lfd.uci.edu/~gohlke/pythonlibs/!

Java Android: how to find imports? (same namespace...)
Need to parse all class names in a file: new FancyObject(...)
and see if it is a file in the namespace...
Same with C++

from pygments.lexers import JavaLexer

lexer = JavaLexer()
tokens = lexer.get_tokens(src)

# TODO: GitHub API call to get all files in the folder (namespace)

for t in tokens:
    print(str(t[0]))   # 'Token.Name                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               '

https://lornajane.net/posts/2011/uml-diagrams-with-graphviz
http://www.ffnn.nl/pages/articles/media/uml-diagrams-using-graphviz-dot.php


TODO:

Either:
1. Mark as invalid and close
2. Classify and assign

Enforce issues template, for example:

# Summary
put summary here, this will be parsed. please enclose code strings in grave accents (``) so there they will be escaped

# Version
put version here, e.g. 1.2.0

# Logs / Errors
```
paste logs here
```

# Links to affected files (if possible):
1. [GitHub](put_link_here)
2. [GitHub](put_link_here)
3. [GitHub](put_link_here)
'''

# HTTP libraries
from flask import Flask, jsonify, make_response, request, send_from_directory, abort, redirect, render_template, render_template_string
from flask_cors import CORS

from urllib.parse import urlencode
from urllib.request import urlopen, Request

# NLP libraries
# from gensim import corpora, models, similarities, downloader
from gensim.corpora.dictionary import Dictionary
from gensim.models.ldamodel import LdaModel
from gensim.parsing.preprocessing import preprocess_documents
from gensim.test.utils import common_texts

import matplotlib.pyplot as plt      # Don't know whether this is needed

import spacy
from spacy.lang.en.stop_words import STOP_WORDS

from wordcloud import WordCloud

# Standard library
from base64 import b64encode, b64decode
from json import dumps, loads
from pprint import pprint
from re import sub

app = Flask(__name__)
CORS(app)

'''
https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps
'''
@app.route('/', methods = ['GET'])
def index():
	return redirect('login')

@app.route('/login', methods = ['GET'])
def login():
	'''
	ImmutableMultiDict([('error', 'access_denied'), ('error_description', 'The user has denied your application access.'), ('error_uri', 'https://docs.github.com/apps/managing-oauth-apps/troubleshooting-authorization-request-errors/#access-denied')])
	ImmutableMultiDict([('code', 'c9427c0daabef591bec8')])
	'''
	print(request.method)
	print(request.json)
	print(request.args)

	if 'code' not in request.args:
		query = {
			'client_id': '34ed33a5c053d0c8e014',
			'redirect_uri': 'https://dord.mynetgear.com:5351/login',
			'allow_signup': False
		}
		return redirect(f'https://github.com/login/oauth/authorize?{urlencode(query)}')
	else:
		url = 'https://github.com/login/oauth/access_token'

		headers = {
			'Accept': 'application/json',
			'Content-Type': 'application/json'
		}

		body = {'client_id': '34ed33a5c053d0c8e014',
		 'client_secret': '446a323da8084af5dc13db5beed18bb85b778da2',
		 'code': request.args['code']
		 }	

		data = dumps(body).encode('utf-8')
		print(data)

		req = Request(url, data=data)
		for h in headers:
			req.add_header(h, headers[h])

		try:
			res = urlopen(req)
			# print(res.info())
		except Exception as e:
			print(e.read())

		# Set cookies
		cookieContent = loads(res.read())
		response = make_response(redirect('/dashboard'))
		response.set_cookie('access_token', cookieContent['access_token'])
		return response

def getUserInfo():
	# Get auth'd user's name and avatar
	url = 'https://api.github.com/user'

	req = Request(url)

	tok = request.cookies.get('access_token')

	headers = {
		'Accept': '*/*',
		'Content-Type': 'application/json',
		'Authorization': f"token {tok}"
	}
	for h in headers:
		req.add_header(h, headers[h])

	res = urlopen(req)
	resJson = loads(res.read())

	return resJson

@app.route('/dashboard', methods = ['GET'])
def dashboard():
	userInfo = getUserInfo()
	###########################

	# Get all repos and stuff them into the template
	url = 'https://api.github.com/user/repos?sort=pushed&per_page=100'

	req = Request(url)

	tok = request.cookies.get('access_token')

	headers = {
		'Accept': '*/*',
		'Content-Type': 'application/json',
		'Authorization': f"token {tok}"
	}
	for h in headers:
		req.add_header(h, headers[h])

	res = urlopen(req)
	resJson2 = loads(res.read())

	for cnt in range(len(resJson2)):
		if resJson2[cnt]['language'] is not None:
			resJson2[cnt]['language'] = resJson2[cnt]['language'].replace('++','plusplus').replace('#','sharp').replace('HTML','html5').split(' ')[0]

	pprint(resJson2)
	open_issues = sum([x['open_issues'] for x in resJson2])
	open_issue_repos = sum([1 for x in resJson2 if x != 0])

	wordcloud = topicModelling()

	return render_template('index.html', segment='index', 
		avatar=userInfo['avatar_url'], usrname=userInfo['login'], name=userInfo['name'],
		open_issues=open_issues, open_issue_repos=open_issue_repos, repolist=resJson2, wordcloud=wordcloud)



@app.route('/repo/<string:owner>/<string:reponame>', methods = ['GET'])
def repoDetail(owner, reponame):
	userInfo = getUserInfo()
	###########################

	# issues_to_topic(owner, reponame)

	# POST '/markdown'

	url = f'https://api.github.com/repos/SoftFeta/tempusespatium/contents/app/src/main/java/hk/edu/cuhk/cse/tempusespatium/Round1Activity.java'

	req = Request(url)

	tok = request.cookies.get('access_token')

	headers = {
		'Accept': '*/*',
		'Content-Type': 'application/json',
		'Authorization': f"token {tok}"
	}
	for h in headers:
		req.add_header(h, headers[h])

	res = urlopen(req)
	resJson = loads(res.read())

	code = b64decode(resJson['content'].encode('utf-8')).decode('utf-8')
	print(code)

	lexer = find_lexer_class_for_filename(url) #guess_lexer(code)
	print(lexer)
	parsedHtml = highlight(code, lexer(), HtmlFormatter(linenos='table'))
	print(parsedHtml)

	return render_template('repo.html', segment='index', 
		avatar=userInfo['avatar_url'], usrname=userInfo['login'], name=userInfo['name'],
		open_issues=None, open_issue_repos=None, repoowner=owner, reponame=reponame,
		parsed = parsedHtml)


'''
from os import getpid
from psutil import Process
process = psutil.Process(getpid())
>> pmem(rss=14929920, vms=7827456, num_page_faults=3820, peak_wset=14929920, wset=14929920, peak_paged_pool=132280, paged_pool=132104, peak_nonpaged_pool=13888, nonpaged_pool=13712, pagefile=7827456, peak_pagefile=7827456, private=7827456)
print(process.memory_info().rss)               # In bytes
>> 14929920
'''
@app.route('/performanceTestInDocker/<string:owner>/<string:reponame>', methods = ['GET'])
def performanceTestInDocker(owner, reponame):
	userInfo = getUserInfo()
	###########################

	tok = request.cookies.get('access_token')
	headers = {
		'Accept': '*/*',
		'Content-Type': 'application/json',
		'Authorization': f"token {tok}"
	}

	url = 'https://api.github.com/repos/SoftFeta/tempusespatium/git/trees/master?recursive=1'
	
	res = urlopen(url)
	resJson = loads(res.read())

	print([x['path'] for x in resJson['tree'] if x['path'].endswith('.java')])
	return '<Loading bar> Check back a couple of minutes.'


'''
https://docs.github.com/en/rest/reference/git#get-a-tree
'''
@app.route('/generateClassUml/<string:owner>/<string:reponame>', methods = ['GET'])
def generateClassUml(owner, reponame):
	userInfo = getUserInfo()
	###########################
	url = f'https://api.github.com/repos/SoftFeta/tempusespatium/contents/app/src/main/java/hk/edu/cuhk/cse/tempusespatium/Round1Activity.java'

	req = Request(url)

	tok = request.cookies.get('access_token')

	headers = {
		'Accept': '*/*',
		'Content-Type': 'application/json',
		'Authorization': f"token {tok}"
	}
	for h in headers:
		req.add_header(h, headers[h])

	res = urlopen(req)
	resJson = loads(res.read())

	code = b64decode(resJson['content'].encode('utf-8')).decode('utf-8')
	print(code)

	lexer = find_lexer_class_for_filename(url) #guess_lexer(code)
	print(lexer)
	parsedHtml = highlight(code, lexer(), HtmlFormatter(linenos='table'))
	print(parsedHtml)
	###########################
	tok = request.cookies.get('access_token')
	headers = {
		'Accept': '*/*',
		'Content-Type': 'application/json',
		'Authorization': f"token {tok}"
	}

	url = 'https://api.github.com/repos/SoftFeta/tempusespatium/git/trees/master?recursive=1'
	
	req = Request(url)

	tok = request.cookies.get('access_token')

	headers = {
		'Accept': '*/*',
		'Content-Type': 'application/json',
		'Authorization': f"token {tok}"
	}
	for h in headers:
		req.add_header(h, headers[h])

	res = urlopen(req)
	resJson2 = loads(res.read())

	# Determine the root directory
	javaFiles = [x['path'] for x in resJson2['tree'] if x['path'].endswith('.java')]

	dirnameCounter = Counter([dirname(f) for f in javaFiles])

	root = dirnameCounter.most_common(1)[0][0]

	print('Namespace: ', root)

	includedFiles = [f for f in javaFiles if dirname(f) == root]
	
	entities = [basename(f).split('.')[0] for f in includedFiles]
	
	print('Files: ', entities)

	A = pygraphviz.AGraph()
	for ent in entities:
		A.add_node(ent,shape='box') #color='goldenrod2', style='filled', 
	A.layout()
	graphString = f'<img style="width: 100%;" src="data:image/jpeg;base64,{b64encode(A.draw(None, "jpeg")).decode("utf-8")}">'

	return render_template('repo.html', segment='index', 
		avatar=userInfo['avatar_url'], usrname=userInfo['login'], name=userInfo['name'],
		open_issues=None, open_issue_repos=None, repoowner=owner, reponame=reponame,
		graph = graphString, parsed=parsedHtml)
'''
Set up bug severity scale tags for the repository
'''
def initialiseTagSystem(owner, reponame):
	palette = [('FFCCCC', 'Trivial'),('F6B5B5', 'Trivial'),('EC9F9F', 'Minor'),('E38888', 'Minor'),('D97171', 'Moderate'),
	('D05B5B', 'Moderate'),('C64444', 'Major'),('BD2D2D', 'Major'),('B31717', 'Critical'),('AA0000', 'Critical')]

	tok = request.cookies.get('access_token')
	headers = {
		'Accept': '*/*',
		'Content-Type': 'application/json',
		'Authorization': f"token {tok}"
	}

	cnt = 0

	for lbl in palette:
		url = f"https://api.github.com/repos/{reponame}/{name}/labels"

		body = {
			'name': f'severity:{cnt+1}',
			'color': lbl[0],
			'description': lbl[1]
		}

		data = dumps(body).encode('utf-8')
		print(data)

		req = Request(url, data=data)
		for h in headers:
			req.add_header(h, headers[h])

		try:
			res = urlopen(req)
		except Exception as e:
			print(e.read())
		print(res.read())
		cnt += 1


@app.route('/issuesToTopic/<string:owner>/<string:reponame>', methods = ['GET'])
def issuesToTopic(owner, reponame):
	initialiseTagSystem(owner, reponame)
	return 'under construction'


'''
1. Topic model repos in Topics predefined on GitHub one by one.
2. Classify the repo the user has chosen to one of these Topics.
3. Add severity rating.

Possibly connect to a MongoDB database
Start button -> AJAX
Reference: https://ieeexplore.ieee.org/document/5298419
'''
def topicModelling(doNlp=False):
	repo = 'istio'

	url = f'https://api.github.com/repos/istio/{repo}/issues?per_page=100&state=all'

	req = Request(url)

	tok = request.cookies.get('access_token')

	headers = {
		'Accept': '*/*',
		'Content-Type': 'application/json',
		'Authorization': f"token {tok}"
	}
	for h in headers:
		req.add_header(h, headers[h])

	res = urlopen(req)
	resJson = loads(res.read())
	#pprint(resJson)

	# English only for the time being, TODO: detect language
	nlp = spacy.load("en_core_web_sm")#trf")

	# Remove code strings and code blocks from issue text body
	text = [sub(r'`.*?`','',sub(r'```.*?```', '', x['body'])) for x in resJson if isinstance(x['body'],str)]
	#pprint(text)
	docs = [[chunk.text.lower() for chunk in nlp(t).noun_chunks if chunk.text.lower().replace(' ','').isalpha() and (chunk.text.lower().replace(' ','') not in [*STOP_WORDS, repo]) and len(chunk.text.lower().replace(' ','')) >= 3] for t in text]

	# Generate word cloud for visualisation
	long_string = ','.join(docs[0])
	wordcloud = WordCloud(font_path='C:\\WINDOWS\\Fonts\\SCRIPTBL.TTF', background_color="white", max_words=5000, contour_width=3, contour_color='steelblue')
	wordcloud.generate(long_string)

	# Analyze syntax
	# print("Noun phrases:", [chunk.text for chunk in doc.noun_chunks])
	if doNlp:
		print(docs)
		common_dictionary = Dictionary(docs[1:])
		# TODO: Try TF-ID
		common_corpus = [common_dictionary.doc2bow(t) for t in docs[1:]]

		# Train the model on the corpus
		lda = LdaModel(common_corpus, id2word=common_dictionary, num_topics=10)
		# pprint(lda.get_topics())
		pprint(lda.print_topics())

		lda.inference([common_dictionary.doc2bow(docs[0])])

	# print("Verbs:", [token.lemma_ for token in doc if token.pos_ == "VERB"])

	# # Find named entities, phrases and concepts
	# for entity in doc.ents:
	#     print(entity.text, entity.label_)
	'''
	# Stream a training corpus directly from S3.
	corpus = corpora.MmCorpus("s3://path/to/corpus")

	# Train Latent Semantic Indexing with 200D vectors.
	lsi = models.LsiModel(corpus, num_topics=20)

	# Convert another corpus to the LSI space and index it.
	index = similarities.MatrixSimilarity(lsi[another_corpus])

	# Compute similarity of a query vs indexed documents.
	sims = index[query]
	'''

	return wordcloud.to_svg(embed_font=True)

@app.route('/logout', methods = ['GET'])
def logout():
	#	Delete an app authorization
	tok = request.cookies.get('access_token')
	print(tok)
	url = 'https://api.github.com/applications/34ed33a5c053d0c8e014/grant'

	# Must use Basic Authorization here
	headers = {
		'Accept': 'application/json',
		'Content-Type': 'application/json',
		'Authorization': f"Basic {b64encode('34ed33a5c053d0c8e014:446a323da8084af5dc13db5beed18bb85b778da2'.encode('utf-8')).decode('utf-8')}"
	}

	body = {
		'access_token': tok
	}
	data = dumps(body).encode('utf-8')

	req = Request(url, data=data, method='DELETE')

	for h in headers:
		req.add_header(h, headers[h])

	try:
		res = urlopen(req)
	except Exception as e:
		print(e.read())
	print(res.read())

	return redirect('login')

if __name__ == "__main__":
	app.run(host='0.0.0.0', port=5351, ssl_context=('_internal/cert.pem', '_internal/privkey.pem'))