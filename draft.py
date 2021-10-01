##############################################
#
#   Issue Management + Release Notes Generation
#	(Automatic Bug Triage and Assignment by Topic Modelling)
#   Draft only
#
#	Author:			Alex Poon
#	Date:		  	Sep 30, 2021
#	Last update:  	Sep 30, 2021
#
##############################################

# HTTP libraries
from flask import Flask, jsonify, make_response, request, send_from_directory, abort, redirect, render_template, render_template_string
from flask_cors import CORS

from urllib.parse import urlencode
from urllib.request import urlopen, Request

# NLP libraries
from gensim import corpora, models, similarities, downloader			# Topic Modelling
import matplotlib.pyplot as plt
from wordcloud import WordCloud

# Standard library
from base64 import b64encode, b64decode
from json import dumps

app = Flask(__name__)
CORS(app)

'''
https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps
'''
# @app.route('/login', methods = ['GET'])
# def login():
# 	return redirect('https://github.com/login/oauth/authorize?client_id=34ed33a5c053d0c8e014&redirect_uri=https://dord.mynetgear.com:5285/login2&allow_signup=false')

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
			'redirect_uri': 'https://dord.mynetgear.com:5285/login',
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

@app.route('/dashboard', methods = ['GET'])
def dashboard():
	return render_template('.html')

@app.route('/logout', methods = ['GET'])
def logout():
	return

'''
https://dord.mynetgear.com:5285/issuesToTopic
'''
@app.route('/issuesToTopic', methods = ['GET'])
def issues_to_topic(repos=['https://github.com/SoftFeta/SWEnggTestRepo']):
	
	# Use my account for the time being. Of course, the username and password will not be published.
	json = {}
	if 'token' not in json:
		json['token'] = 'Z2hwX2JOczFHSTZPWUZmb0ZoMXpqQlBHeFhVYnVxUVB2MTRjUFVVQg=='
		with open('_internal/credentials.txt', 'r') as f:
			json['u'], json['p'] = f.readlines()

	palette = [('FFCCCC', 'Trivial'),('F6B5B5', 'Trivial'),('EC9F9F', 'Minor'),('E38888', 'Minor'),('D97171', 'Moderate'),
	('D05B5B', 'Moderate'),('C64444', 'Major'),('BD2D2D', 'Major'),('B31717', 'Critical'),('AA0000', 'Critical')]

	cnt = 0
	for lbl in palette:
		url = f"https://api.github.com/repos/{repos[0].split('/')[-2]}/{repos[0].split('/')[-1]}/labels"

		auth = f"{json['u']}:{json['p']}"
		headers = {
			'Accept': '*/*',
			'Content-Type': 'application/json',
			'Authorization': f"Basic {b64encode(auth.encode('utf-8')).decode('utf-8')}"
		}

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

#  Possibly connect to a MongoDB database for topic modelling?
#  By topic modelling, word cloud maybe
def topicModelling():
	# Stream a training corpus directly from S3.
	corpus = corpora.MmCorpus("s3://path/to/corpus")

	# Train Latent Semantic Indexing with 200D vectors.
	lsi = models.LsiModel(corpus, num_topics=20)

	# Convert another corpus to the LSI space and index it.
	index = similarities.MatrixSimilarity(lsi[another_corpus])

	# Compute similarity of a query vs indexed documents.
	sims = index[query]


if __name__ == "__main__":
	app.run(host='0.0.0.0', port=5285, ssl_context=('_internal/cert.pem', '_internal/privkey.pem'))