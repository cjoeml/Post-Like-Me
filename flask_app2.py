# coding: utf-8
import markovify 
from flask import Flask
from flask import g, session, request, url_for, flash
from flask import redirect, render_template
from flask_oauthlib.client import OAuth
from flask_bootstrap import Bootstrap
import twitter
import json

app = Flask(__name__)
app.debug = True
app.secret_key = 'development'

##################

def get_keys_and_secrets():
    """
    Function to aggregate all keys and secrets for simplicity and return an easy tuple to parse
    """
    ## Need to add your own details.json with your keys and secrets ##
    credentials = {}
    with open("details.json",'r') as file:
        credentials = json.load(file)[0]
        consumer_key = credentials["consumer_key"]
        consumer_secret = credentials["consumer_secret"]
        access_token_key = credentials["access_token_key"]
        access_token_secret = credentials["access_token_secret"]
        return (consumer_key, consumer_secret, access_token_key, access_token_secret)

####################

## API calling here ##
key_tuple = get_keys_and_secrets()
api = twitter.Api(consumer_key=key_tuple[0],
                  consumer_secret=key_tuple[1],
                  access_token_key=key_tuple[2],
                  access_token_secret=key_tuple[3])

oauth = OAuth(app)

twitter = oauth.remote_app(
    'twitter',
    consumer_key=key_tuple[0],
    consumer_secret=key_tuple[1],
    base_url='https://api.twitter.com/1.1/',
    request_token_url='https://api.twitter.com/oauth/request_token',
    access_token_url='https://api.twitter.com/oauth/access_token',
    authorize_url='https://api.twitter.com/oauth/authorize'
)

print(twitter)

@twitter.tokengetter
def get_twitter_token():
    if 'twitter_oauth' in session:
        resp = session['twitter_oauth']
        return resp['oauth_token'], resp['oauth_token_secret']


@app.before_request
def before_request():
    g.user = None
    if 'twitter_oauth' in session:
        g.user = session['twitter_oauth']


## Index page ##
@app.route("/", methods=['GET'])
def index():
    markov_t = ""
    mkTweet = ""
    tweets = None
    if g.user is not None:
        resp = twitter.request('statuses/home_timeline.json')
        if resp.status == 200:
            tweets = resp.data

        try:
            statuses = api.GetUserTimeline(screen_name=g.user['screen_name'], count="200")
            for status in statuses:
                markov_t = markov_t + " " + status.text.strip('\"') + " "
                mkText = markovify.Text(markov_t)
                mkTweet = mkText.make_short_sentence(140)
        except: 
            mkTweet = "Not enough tweets to display Markov tweet."

        else:
            flash('Unable to load tweets from Twitter. Getting statuses from api call.')
            statuses = api.GetUserTimeline(screen_name=g.user['screen_name'], count="200")
            try:
                for status in statuses:
                    markov_t = markov_t + " " + status.text + " "
                    mkText = markovify.Text(markov_t)
                    mkTweet = mkText.make_short_sentence(140)
            except:
                mkTweet = "Not enough tweets to display Markov tweet."
    # mkTweet = 'e'
    return render_template('index2.html', tweets=tweets, mkv=mkTweet)


@app.route('/tweet', methods=['POST'])
def tweet():
    if g.user is None:
        return redirect(url_for('login', next=request.url))
    status = request.form['tweet']
    if not status:
        return redirect(url_for('index'))
    resp = twitter.post('statuses/update.json', data={
        'status': status
    })

    if resp.status == 403:
        flash("Error: #%d, %s " % (
            resp.data.get('errors')[0].get('code'),
            resp.data.get('errors')[0].get('message'))
        )
    elif resp.status == 401:
        flash('Authorization error with Twitter.')
    else:
        flash('Successfully tweeted your tweet (ID: #%s)' % resp.data['id'])
    return redirect(url_for('index'))


@app.route('/login')
def login():
    callback_url = url_for('oauthorized', next=request.args.get('next'))
    return twitter.authorize(callback=callback_url or request.referrer or None)


@app.route('/logout')
def logout():
    session.pop('twitter_oauth', None)
    return redirect(url_for('index'))


@app.route('/oauthorized')
def oauthorized():
    resp = twitter.authorized_response()
    if resp is None:
        flash('You denied the request to sign in.')
    else:
        session['twitter_oauth'] = resp
    return redirect(url_for('index'))

## Results page - this is where we POST ##
@app.route("/results", methods=['GET','POST'])
def results():
    if request.method == "POST":
        user = request.form['search_input']

    statuses = ""

    ## Basic API call ##
    try:
        statuses = api.GetUserTimeline(screen_name=user)
    except:
        user = ""

    ## Build page ##
    return render_template('results.html', user=user, statuses=statuses)


if __name__ == '__main__':
    app.run()