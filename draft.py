##############################################
#
#   Issue Management + Release Notes Generation
#   (Automatic Bug Triage and Assignment by Topic Modelling)
#   Draft only
#
#	Author:          Alex Poon
#	Date:           Sep 30, 2021
#	Last update:    Sep 30, 2021
#
##############################################

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
			print(res.info())
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

@app.route('/repo/<string:owner>/<string:name>', methods = ['GET'])
def repoDetail(owner, name):
	userInfo = getUserInfo()
	###########################

	return render_template('index.html', segment='index', 
		avatar=userInfo['avatar_url'], usrname=userInfo['login'], name=userInfo['name'],
		open_issues=None, open_issue_repos=None, repolist=[])

@app.route('/logout', methods = ['GET'])
def logout():
	#	TODO: Remove the cookie
	return

'''
Set up bug severity scale tags for the repository
'''
@app.route('/issuesToTopic/<string:owner>/<string:name>', methods = ['GET'])
def issues_to_topic(owner, name):

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
		url = f"https://api.github.com/repos/{owner}/{name}/labels"

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

	return 'es klappt'

'''
1. Topic model repos in Topics predefined on GitHub one by one.
2. Classify the repo the user has chosen to one of these Topics.
3. Add severity rating.

Possibly connect to a MongoDB database
Start button -> AJAX
https://ieeexplore.ieee.org/document/5298419
'''
def topicModelling():
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
	pprint(resJson)

	# English only for the time being, TODO: detect language
	nlp = spacy.load("en_core_web_trf")

	from random import randint

	# Remove code strings and code blocks from issue text body
	text = [sub(r'`.*?`','',sub(r'```.*?```', '', x['body'])) for x in resJson]
	pprint(text)
	docs = [[chunk.text.lower() for chunk in nlp(t).noun_chunks if chunk.text.lower().replace(' ','').isalpha() and (chunk.text.lower().replace(' ','') not in [*STOP_WORDS, repo]) and len(chunk.text.lower().replace(' ','')) >= 3] for t in text]

	# Generate word cloud for visualisation
	long_string = ','.join(docs[1])
	wordcloud = WordCloud(font_path='C:\\WINDOWS\\Fonts\\SCRIPTBL.TTF', background_color="white", max_words=5000, contour_width=3, contour_color='steelblue')
	wordcloud.generate(long_string)


	# Analyze syntax
	# print("Noun phrases:", [chunk.text for chunk in doc.noun_chunks])
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

if __name__ == "__main__":
	app.run(host='0.0.0.0', port=5351, ssl_context=('_internal/cert.pem', '_internal/privkey.pem'))