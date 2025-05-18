import os
import re
import json
import tweepy
from datetime import datetime, timedelta
from collections import defaultdict
from textblob import TextBlob
import requests
from openai import OpenAI
from supabase import create_client

# Load credientials
with open('credientials.json', 'r') as f:
    creds = json.load(f)

x_auth_bearer = creds['x_auth_bearer']
x_auth_bearer_2 = creds['x_auth_Bearer_2']
BEARER_TOKEN = creds['x_auth_bearer_3']
CONSUMER_API_KEY = creds['x_consumer_api_key']
CONSUMER_API_SECRET_KEY = creds['x_consumer_api_secret_key']
ACCESS_TOKEN = creds['x_access_token']
ACCESS_TOKEN_SECRET = creds['x_access_token_secret']
CLIENT_ID = creds['x_client_id']
CLIENT_SECRET = creds['x_client_secret']
DEEPSEEK_API_KEY = creds['deepseek_api_key']
DEEPSEEK_API_URL = creds['deepseek_api_url']
OPENAI_API_KEY = creds['openai_api_key']
SUPABASE_URL = creds['supabase_url']
SUPABASE_KEY = creds['supabase_key']
USERNAME = "VirtusCenturion"

# Authenticate with 1.0a User Context
twitter_client_V1 = tweepy.Client(
    consumer_key = CONSUMER_API_KEY,
    consumer_secret = CONSUMER_API_SECRET_KEY,
    access_token = ACCESS_TOKEN,
    access_token_secret = ACCESS_TOKEN_SECRET
)

# Authenticate with 2.0 Bearer Token (App-Only)
twitter_client_V2 = tweepy.Client(bearer_token=BEARER_TOKEN)

auth1 = tweepy.OAuth1UserHandler(
    consumer_key = CONSUMER_API_KEY,
    consumer_secret = CONSUMER_API_SECRET_KEY,
    access_token = ACCESS_TOKEN,
    access_token_secret = ACCESS_TOKEN_SECRET
)

api1 = tweepy.API(auth1)

# Initialize OpenAI client
# openai_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Supabase setup
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# List of bots, hashtags, and keywords
bots = ['tri_sigma_', 'kwantxbt', 'Nostradamu_ai', 'aixbt_agent', 'Kudai_IO']
hashtags = ['AI', 'DEFAI', 'DeFAI', 'RWA', 'AI16Z', 'DeFi', '0x0']
keywords = ['ai agent', 'ai coin', 'bullish', 'ATH', '100X', 'on-chain']

# Function to search tweets using Twitter API v2
def search_tweets(query, max_tweets=10):
    try:
        # Calculate the start time (48 hours ago)
        start_time = (datetime.utcnow() - timedelta(hours=48)).isoformat() + "Z"

        # Fetch tweets with the specified query, excluding replies and retweets, and within the last 48 hours
        tweets = twitter_client_V2.search_recent_tweets(
            query=f"{query} -is:reply -is:retweet",
            max_results=max_tweets * 2,  # Fetch extra tweets to account for filtering
            tweet_fields=['public_metrics', 'created_at', 'entities', 'author_id'],
            expansions=['author_id'],
            user_fields=['verified_type'],  # Fetch verified status of the author
            start_time=start_time  # Filter tweets from the last 48 hours
        )
        # tweets = twitter_client.search_tweets(
        #     q=f"{query} -filter:replies -filter:retweets",
        #     count=max_tweets * 2,  # Fetch extra tweets to account for filtering
        #     tweet_mode="extended",
        #     until=(datetime.utcnow() - timedelta(hours=48)).strftime('%Y-%m-%d')  # Filter tweets from the last 48 hours
        # )
        return tweets
    except Exception as e:
        print(f"Error searching tweets: {e}")
        return None

# Function to filter tweets by likes, retweets, and additional criteria
def filter_tweets(tweets):
    filtered_tweets = []
    if not tweets or not tweets.data:
        return filtered_tweets

    # Create a mapping of author_id to user details
    user_map = {user.id: user for user in tweets.includes['users']}

    for tweet in tweets.data:
        # Check if the tweet meets the basic criteria
        if (
            tweet.public_metrics['like_count'] >= 20
            and tweet.public_metrics['retweet_count'] >= 5
            and tweet.public_metrics['reply_count'] >= 5
        ):
            # Additional filters
            if (
                not is_spammy(tweet)
                and is_positive(tweet)
                and user_map.get(tweet.author_id).verified_type == 'blue'
            ):
                filtered_tweets.append(tweet)
                if len(filtered_tweets) >= 5:  # Stop once we have 10 filtered tweets
                    break
    return filtered_tweets

# Function to check if a tweet is spammy
def is_spammy(tweet):
    # Check for excessive links, hashtags, or promotional phrases
    text = tweet.text.lower()
    link_count = len(re.findall(r'http[s]?://\S+', text))
    hashtag_count = len(re.findall(r'#\w+', text))
    promotional_phrases = ['buy now', 'limited offer', 'discount', 'click here', 'sign up']

    if (
        link_count > 2  # More than 2 links
        or hashtag_count > 3  # More than 3 hashtags
        or any(phrase in text for phrase in promotional_phrases)  # Contains promotional phrases
    ):
        return True
    return False

# Function to check if a tweet has a positive sentiment
def is_positive(tweet):
    analysis = TextBlob(tweet.text)
    return analysis.sentiment.polarity > 0  # Positive sentiment

# Function to group similar tweets and pick the most engaging one
def group_and_pick_best(tweets):
    grouped_tweets = defaultdict(list)
    for tweet in tweets:
        # Use a simplified version of the text for grouping (remove links and hashtags)
        simplified_text = re.sub(r'http[s]?://\S+', '', tweet.text)  # Remove links
        simplified_text = re.sub(r'#\w+', '', simplified_text)  # Remove hashtags
        simplified_text = simplified_text.strip().lower()
        grouped_tweets[simplified_text].append(tweet)

    best_tweets = []
    for group in grouped_tweets.values():
        # Pick the most engaging tweet in the group (highest likes + retweets)
        best_tweet = max(group, key=lambda x: x.public_metrics['like_count'] + x.public_metrics['retweet_count'])
        best_tweets.append(best_tweet)
    return best_tweets

# Function to paraphrase a tweet using DeepSeek API
def paraphrase_tweet(text):
    headers = {
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'text': text,
        'mode': 'standard'
    }
    response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        return response.json().get('paraphrased_text', text)
    else:
        print(f"Error paraphrasing tweet: {response.status_code}")
        return text

# Function to generate a relevant and attractive post using DeepSeek API
def generate_post(tweets):
    """
    Generate a relevant and attractive post using OpenAI API.
    """
    # Prepare the input prompt for the OpenAI API
    # prompt = f"""
    # You are a social media manager for a trending tech and crypto account. Your task is to create an engaging and positive post based on the following curated tweets:

    # Tweets:
    # {format_tweets_for_prompt(tweets)}

    # Guidelines:
    # 1. Ignore spammy or overly promotional tweets.
    # 2. Focus on trending topics and themes.
    # 3. Keep the tone positive and engaging. You can use slang language to make the post more relatable and fun, but ensure the overall tone remains positive.
    # 4. Use hashtags wisely (2-3 relevant hashtags).

    # Write a post that summarizes the tweets in a concise and engaging way. Include a trending theme if applicable.
    # """
    prompt = f"""
    You are a social media manager for a trending tech and crypto account. Your task is to create an engaging and positive post based on the following curated tweets:

    Tweets:
    {format_tweets_for_prompt(tweets)}

    Guidelines:
    1. Analyze the tweets and decide whether to focus on specific coins or summarize general trends.
    2. If specific coins (e.g., BTC, ETH, SOL) are heavily discussed, create a post highlighting those coins.
    3. If no specific coins are heavily discussed, summarize the general trends in the crypto and AI space.
    4. Ignore spammy or overly promotional tweets.
    5. Keep the tone positive and engaging. You can use slang language to make the post more relatable and fun, but ensure the overall tone remains positive.
    6. Use hashtags wisely (2-3 relevant hashtags).
    7. Keep the tweet short and concise (280 characters or less).

    Write a post that summarizes the tweets in a concise and engaging way.
    """

    response = openai_client.chat.completions.create(
        model="gpt-4",  # Use GPT-4 or GPT-3.5-turbo
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300,  # Adjust based on desired length
        temperature=0.7  # Adjust for creativity
    )
    return response.choices[0].message.content


# Function to format the tweets for the prompt input
def format_tweets_for_prompt(tweets):
    """
    Format the tweets for the prompt input.
    """
    formatted_tweets = []
    for i, tweet in enumerate(tweets, 1):
        formatted_tweets.append(
            f"{i}. {tweet['text']}\n"
            f"   👍 Likes: {tweet['likes']}, 🔁 Retweets: {tweet['retweets']}\n"
            f"   👤 Author: {tweet['author']} {'✅' if tweet['verified'] else ''}"
        )
    return "\n".join(formatted_tweets)

# Function to split text into chunks of 280 characters
def split_text_into_chunks(text, max_length=280):
    """
    Split text into chunks of max_length characters.
    """
    chunks = []
    while len(text) > max_length:
        # Find the last space within the limit
        split_index = text.rfind(' ', 0, max_length)
        if split_index == -1:
            split_index = max_length
        chunks.append(text[:split_index].strip())
        text = text[split_index:].strip()
    chunks.append(text)
    return chunks

# Function to post a tweet thread
def post_tweet_thread(text):
    """
    Post a tweet thread if the text exceeds the character limit.
    """
    chunks = split_text_into_chunks(text)
    if not chunks:
        print("No text to post.")
        return

    # Post the first tweet
    try:
        response = twitter_client_V1.create_tweet(text=chunks[0])
        print("First tweet posted successfully!")
        print(f"Tweet ID: {response.data['id']}")
        previous_tweet_id = response.data['id']
    except Exception as e:
        print(f"Error posting first tweet: {e}")
        return

    # Post the remaining tweets as replies
    for chunk in chunks[1:]:
        try:
            response = twitter_client_V1.create_tweet(text=chunk, in_reply_to_tweet_id=previous_tweet_id)
            print("Next tweet posted successfully!")
            print(f"Tweet ID: {response.data['id']}")
            previous_tweet_id = response.data['id']
        except Exception as e:
            print(f"Error posting reply tweet: {e}")

def like_n_comment_tweet(tweets):
    """
    Like and comment on 1 to 3 top tweets based on engagement metrics.
    """
    if not tweets:
        print("No tweets to like or comment on.")
        return

    # Sort tweets by engagement (likes + retweets + replies)
    sorted_tweets = sorted(
        tweets,
        key=lambda x: x['likes'] + x['retweets'],
        reverse=True
    )

    # Select top 1 to 3 tweets
    top_tweets = sorted_tweets[:min(3, len(sorted_tweets))]

    for tweet in top_tweets:
        try:
            # Like the tweet
            twitter_client_V1.like(tweet['id'])
            print(f"Liked tweet ID: {tweet['id']}")

            # Generate a relevant comment using OpenAI API
            prompt = f"""
            You are a social media manager for a trending tech and crypto account. Your task is to write a short, engaging, and attractive comment for the following tweet:

            Tweet:
            {tweet['text']}

            Guidelines:
            1. Keep the comment very short (1-2 sentences max).
            2. Use a casual, fun, and engaging tone.
            3. Use slang, emojis, and trending phrases to make the comment relatable and attractive.
            4. If the tweet is about a specific coin or trend, mention it in a fun way.
            5. Avoid spammy or overly promotional language.
            6. Make it sound like a real person, not a bot.
            7. Always maintain a positive vibe—no negativity or criticism.

            Write a comment that adds value and grabs attention.
            """

            response = openai_client.chat.completions.create(
                model="gpt-4",  # Use GPT-4 or GPT-3.5-turbo
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,  # Keep the comment short
                temperature=0.7  # Adjust for creativity
            )

            comment = response.choices[0].message.content

            # Post the comment as a reply to the tweet
            twitter_client_V1.create_tweet(
                text=comment,
                in_reply_to_tweet_id=tweet['id']
            )
            print(f"Commented on tweet ID: {tweet['id']}")
            print(f"Comment: {comment}")

        except Exception as e:
            print(f"Error liking or commenting on tweet ID {tweet['id']}: {e}")

# Save tweet in json formate:
def save_log(all_tweets, refined_tweets, post):
    log_json = {
        'all_tweet': [
            {
                "text": tweet.text,
                "likes": tweet.public_metrics['like_count'],
                "retweets": tweet.public_metrics['retweet_count'],
                "author": tweet.author_id
            }
            for tweet in all_tweets
        ],
        'refined_tweets': refined_tweets,
        'generated_tweet': post
    }
    with open(f'data/generated/{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}_log.json', 'w') as file:
        json.dump(log_json, file, indent=4)

def fetch_account_stats(username):
    user = twitter_client_V2.get_user(username=username, user_fields=["public_metrics"])
    stats = user.data.public_metrics
    return {
        "username": username,
        "date": datetime.utcnow().date().isoformat(),
        "followers": stats["followers_count"],
        "following": stats["following_count"],
        "tweets": stats["tweet_count"],
        "listed": stats["listed_count"],
        "favorites": get_favorites_sum(user.data.id),
        "mentions": get_mention_count(user.data.id)
    }

def get_favorites_sum(user_id):
    tweets = twitter_client_V2.get_users_tweets(id=user_id, tweet_fields=["public_metrics"], max_results=10)
    return sum(tweet.public_metrics["like_count"] for tweet in tweets.data)

def get_mention_count(user_id):
    mentions = twitter_client_V2.get_users_mentions(id=user_id, max_results=10)
    return len(mentions.data) if mentions.data else 0

def fetch_all_tweets(user_id):
    all_tweets = []
    next_token = None

    # while True:
    response = twitter_client_V2.get_users_tweets(
        id=user_id,
        tweet_fields=["public_metrics", "created_at"],
        max_results=100,
        pagination_token=next_token
    )

    if response.data:
        for tweet in response.data:
            metrics = tweet.public_metrics
            all_tweets.append({
                "id": str(tweet.id),
                "text": tweet.text,
                "created_at": tweet.created_at.isoformat(),
                "likes": metrics["like_count"],
                "retweets": metrics["retweet_count"],
                "replies": metrics["reply_count"],
                "interactions": sum(metrics.values())
            })

    next_token = response.meta.get("next_token")
        # if not next_token:
        #     break

    return all_tweets
def fetch_replies_to_my_tweets(username):
    query = f"to:{username}"
    search = twitter_client_V2.search_recent_tweets(query=query, tweet_fields=["author_id", "in_reply_to_user_id", "created_at", "public_metrics"], max_results=100)
    replies = []
    if search.data:
        for tweet in search.data:
            metrics = tweet.public_metrics
            replies.append({
                "id": str(tweet.id),
                "tweet_id": str(tweet.referenced_tweets[0].id) if tweet.referenced_tweets else None,
                "text": tweet.text,
                "author_id": tweet.author_id,
                "created_at": tweet.created_at.isoformat(),
                "likes": metrics["like_count"],
                "retweets": metrics["retweet_count"],
                "replies": metrics["reply_count"]
            })
    return replies

def fetch_liked_tweets(user_id):
    liked = twitter_client_V2.get_liked_tweets(id=user_id, tweet_fields=["public_metrics", "author_id", "created_at"], max_results=100)
    liked_data = []
    if liked.data:
        for tweet in liked.data:
            metrics = tweet.public_metrics
            liked_data.append({
                "id": str(tweet.id),
                "text": tweet.text,
                "author_id": tweet.author_id,
                "created_at": tweet.created_at.isoformat(),
                "likes": metrics["like_count"],
                "retweets": metrics["retweet_count"],
                "replies": metrics["reply_count"]
            })
    return liked_data

def push_to_supabase(stats, tweets, replies):
    supabase.table("account_stats").insert(stats).execute()
    for tweet in tweets:
        supabase.table("tweets").upsert(tweet, on_conflict=["id"]).execute()
    for reply in replies:
        supabase.table("replies").upsert(reply, on_conflict=["id"]).execute()

# Main function
def main():
    all_tweets = []

    # Search tweets from bots
    for bot in bots:
        query = f'from:{bot}'
        tweets = search_tweets(query)
        filtered_tweets = filter_tweets(tweets)
        all_tweets.extend(filtered_tweets)
        print(f"Found {len(filtered_tweets)} tweets from {bot}")

    # Search tweets with hashtags
    for hashtag in hashtags:
        query = f'#{hashtag}'
        tweets = search_tweets(query)
        filtered_tweets = filter_tweets(tweets)
        all_tweets.extend(filtered_tweets)
        print(f"Found {len(filtered_tweets)} tweets with #{hashtag}")

    # Search tweets with keywords
    for keyword in keywords:
        query = f'{keyword}'
        tweets = search_tweets(query)
        filtered_tweets = filter_tweets(tweets)
        all_tweets.extend(filtered_tweets)
        print(f"Found {len(filtered_tweets)} tweets with keyword: {keyword}")

    # Group similar tweets and pick the best one
    all_tweets = group_and_pick_best(all_tweets)

    # Refine tweets using DeepSeek API
    refined_tweets = []
    for tweet in all_tweets:
        # refined_text = paraphrase_tweet(tweet.text)
        user = twitter_client_V2.get_user(id=tweet.author_id, user_fields=['verified_type', 'username'])
        refined_tweets.append({
            'id': tweet.id,
            'text': tweet.text,
            'likes': tweet.public_metrics['like_count'],
            'retweets': tweet.public_metrics['retweet_count'],
            'author': user.data.username,
            'verified': user.data.verified_type
        })

    # Generate and print the final post
    post = generate_post(refined_tweets)
    print("\nFinal Post:\n")
    print(post)

    save_log(all_tweets, refined_tweets, post)
    post_tweet_thread(post)
    like_n_comment_tweet(refined_tweets)
    
    user = twitter_client_V2.get_user(username=USERNAME)
    stats = fetch_account_stats(USERNAME)
    tweets = fetch_all_tweets(user.data.id)
    replies = fetch_replies_to_my_tweets(USERNAME)
    push_to_supabase(stats, tweets, replies)

    print("Done.")

if __name__ == "__main__":
    main()