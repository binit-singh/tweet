import tweepy
import csv
import sqlite3

# twitter api setup
access_token = "3159517387-QOtt7KPSYxKlWYlMw7t1DZuwDPhtzeivSyX5GTm"
access_token_secret = "cVB2nXfFufYliZh63JwntFcUpioO4C35upHxphc6ijeXu"
consumer_key = "3NWtMkxDE1SlZQE13bnwUnQe0"
consumer_secret = "82p0XbNo67EJWApxGidNylICuVMInnAsRK2vyzh5WtOp9BCAX9"
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)
handle_list = ['@VodafoneIN']

# sqlite db setup
conn = sqlite3.connect('/home/binit/Projects/twitterbot/tweetDB.db')
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

def get_tweets_reply(tweet_list):
	"""
	It will take list of tweets and generate reply_list
	param: tweet_list: [[tweet_id, tweet, name, followers_count], ...]
	return: reply_list : [[reply, name, tweet_id], ...] 
	"""

	return [['hey how are you !!!', 'iam_bhavin', '590139717946978304']]


# Collect tweets and store in db 
for handle in handle_list:
	tweet_list = get_tweets(handle, 10)
	cur.executemany('INSERT INTO user_tweet (handle, tweet_id, user_name, followers_count, tweet) VALUES (?,?,?,?,?)', tweet_list)
	conn.commit()

# Extract tweets from db and generate reply
cur.execute('select tweet, tweet_id, followers_count from user_tweet where processed= 0 and replyed = 0')
collected_tweets = cur.fetchall()
reply_list = get_tweets_reply(collected_tweets)

# Reply to user
for reply in reply_list:
	reply_text = reply[0] + ' @' + reply[1]
	tweet_id = reply[2]
	
	try:
		# Post a status on twiiter
	    api.update_status(status=reply_text, in_reply_to_status_id = tweet_id)
	    # Update reply in table and make processed and replyed True
	    cur.execute("""UPDATE user_tweet SET reply = ? ,processed = ?, replyed = ? WHERE tweet_id= ? """,(reply_text, 1, 1,tweet_id))
	except Exception as e:
	    print 'error', e
	    # Update status failed so only make processed True
        cur.execute("""UPDATE user_tweet SET reply = ? ,processed = ? WHERE tweet_id= ? """,(reply_text, 1,tweet_id))

	conn.commit()





