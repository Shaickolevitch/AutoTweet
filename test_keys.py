import tweepy
import toml

secrets = toml.load('.streamlit/secrets.toml')

client = tweepy.Client(bearer_token=secrets['X_BEARER_TOKEN'])

try:
    user = client.get_user(username='TomerAvital1')
    print('Bearer Token OK — found: @' + user.data.username)
except Exception as e:
    print('Error: ' + str(e))