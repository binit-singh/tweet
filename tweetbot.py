import tweepy
import csv
import sqlite3
import csv
import re
import datetime
import time
from collections import defaultdict
import operator
from textblob import TextBlob
from random import randint

# twitter api setup
access_token = "3158841588-0gzFqnFQnmadAOzP7tr8iVWryV0ucRW7KgtbnUB"
access_token_secret = "yGbrdr3fMW2Lop2izWqwpbRVpvezvCDg6UeEpa0rDqSTg"
consumer_key = "dITvBYqeNSvxtrEl1C6LiTftj"
consumer_secret = "E9M2TVCwOK1ObAEAVfP4LhPKzYL4h9hEALHWNwM6U8ktztm6RB"
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)
response_csv_file = 'response.csv'
handle_list = ['@VodafoneIN', '@airtel_presence', '@aircel', '@RelianceMobile', '@tatadocomo', '@flipkartsupport', '@ICICIBank_Care',
'@HDFCBank_Cares', '@TheOfficialSBI', '@cromaretail', '@idea_cares', '@tatasky', '@snapdeal_help', '@jetairways']
loop_counter = 0
replyed_user_list = []
# sqlite db setup
conn = sqlite3.connect('/home/binit/Projects/tweet/tweetDB.db')
conn.text_factory = str
cur = conn.cursor()

# Create table if not exist to store tweets
create_sql = '''
				create table if not exists user_tweet
				(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL , handle text, tweet_id integer, user_name text,
				 followers_count integer DEFAULT 0, tweet text, processed integer DEFAULT 0, reply text,
				 replyed integer DEFAULT 0)
			 '''
cur.execute(create_sql)
conn.commit()

# Create table if not exist to store list of user's we have replied
create_user_list_sql = '''
				create table if not exists user_list
				(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL , user_name text)
			 '''
cur.execute(create_user_list_sql)
conn.commit()

def processTweet(tweet):
	# process the tweets
	tweet = tweet.decode("utf-8")
	#Convert to lower case
	tweet = tweet.lower()
	#Convert www.* or https?://* to URL
	tweet = re.sub('((www\.[^\s]+)|(https?://[^\s]+))','url',tweet)
	#Convert @username to AT_USER
	tweet = re.sub('@[^\s]+','',tweet)
	#Remove additional white spaces
	tweet = re.sub('[\s]+', ' ', tweet)
	#Replace #word with word
	tweet = re.sub(r'#([^\s]+)', r'\1', tweet)
	#trim
	tweet = tweet.strip('\'"')
	return tweet

def read_response(csv_file):
	file3 = open(csv_file, "rt" )   # file containing words to remove
	reader3 = csv.reader(file3)

	responses = []
	for response in reader3:
		responses.append(str(response[0]))

	return responses


def get_tweets(handle, count):
	"""
	this function will take handle name and return tweets of that handle.
	"""
	tweet_list = []
	try:
		for tweet in tweepy.Cursor(api.search, q=handle, rpp=100, result_type="recent", include_entities=True, lang="en").items(count):
			tweet_list.append([handle, tweet.id, tweet.author.screen_name, tweet.author.followers_count, tweet.text.encode("utf-8")])
	except Exception as e:
		print 'exception', e
		pass

	return tweet_list

def get_tweets_reply(tweet_list, responses):
	"""
	It will take list of tweets and generate reply_list
	param: tweet_list: [[tweet_id, tweet, name, followers_count], ...]
	responses
	return: reply_list : [[reply, name, tweet_id], ...] 
	"""
	user_followers =  defaultdict(int)
	user_tweetid = {}

	for row in tweet_list:
		try:            
			tweet_sentiment_score = 0.0            
			tweet = processTweet(row[1])                   
			blob = TextBlob(tweet)
			for sentence in blob.sentences:
				tweet_sentiment_score += sentence.sentiment.polarity            
				if tweet_sentiment_score < 0.0:
					user_followers[row[2]] = row[3]
					user_tweetid[row[2]] = row[0]

		except Exception, e:
			print 'some error : ', e       

	user_followers_sorted = sorted(user_followers.items(), key=operator.itemgetter(1))

	final_responses = []
	number_of_response = 0
	for name, followers in reversed(user_followers_sorted):    
		if number_of_response < 2:
			response = []        
			response.append(responses[randint(0,len(responses) - 1)])
			response.append(name)
			response.append(user_tweetid[name])        
			final_responses.append(response)
		else:
			break
			number_of_response += 1

	return final_responses

responses = read_response(response_csv_file)

def reply_to_tweet(handle):
	"""
	This function will take 10 tweets from a twitter handle
	chosse 1 best tweet we shold reply and reply it back. 
	"""
	# Collect tweets and store in db 
	tweet_list = get_tweets(handle, 100)
	cur.executemany('INSERT INTO user_tweet (handle, tweet_id, user_name, followers_count, tweet) VALUES (?,?,?,?,?)', tweet_list)
	conn.commit()

	# Extract tweets from db and generate reply
	cur.execute('select tweet_id, tweet, user_name, followers_count from user_tweet where processed= 0 and replyed = 0')
	collected_tweets = cur.fetchall()
	# Extract user list from db
	cur.execute('select user_name from user_list')
	replyed_user_list = cur.fetchall()
	reply_list = get_tweets_reply(collected_tweets, responses)
	try:
		reply = reply_list[0]
		msg = reply[0]
		user = reply[1]
		tweet_id = reply[2]

		# Check if we have already replyed to user today
		if user in replyed_user_list:
			cur.execute('update user_tweet set processed= 1 and replyed = 1 where user_name = %s', user)
			reply_to_tweet(handle)
		else:
			# Reply to user
			reply_text = msg + ' @' + user

			try:
				# Post a status on twiiter
				api.update_status(status=reply_text, in_reply_to_status_id = tweet_id)
				a = 'INSERT INTO user_list (user_name) values ("%s")' % user
				cur.execute(a)
				conn.commit()
				print '='*40,'replyed', '='*40
				print datetime.datetime.now(), user, handle
				print '='*80,

				# Update reply in table and make processed and replyed True
				cur.execute("""UPDATE user_tweet SET reply = ? ,processed = ?, replyed = ? WHERE tweet_id= ? """,(reply_text, 1, 1,tweet_id))
			except Exception as e:
				print 'error as', e
				# Update status failed so only make processed True
				cur.execute("""UPDATE user_tweet SET reply = ? ,processed = ? WHERE tweet_id= ? """,(reply_text, 1,tweet_id))

			conn.commit()
	except:
		pass

for handle in handle_list:
	reply_to_tweet(handle)
	time.sleep(60*2)

	





