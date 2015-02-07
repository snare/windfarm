import twitter
import time
import random
import logging
import threading
from threading import Timer

from scruffy.state import State

import windfarm

log = logging.getLogger('bot')


class ConfigException(Exception): pass


class WindfarmBot(object):
    def __init__(self, config=None):
        if not config:
            self.config = windfarm.config
        self.done = None
        self.creds = None
        self.tweet_timer = None
        self.mention_timer = None
        self.search_timer = None
        self.state = State(windfarm.env['state'])

        # check config
        c = self.config.api_keys
        for s in [c.consumer_key, c.consumer_secret, c.access_key, c.access_secret]:
            if s == 'xxx':
                raise ConfigException("You need to specify the Twitter keys and secrets in the config. These go in "
                                      "~/.windfarm/config (see default.cfg for the format).")

        # load causes and effects
        self.causes = []
        self.causes.extend(map(lambda x: (x,True), list(self.config.causes.singular)))
        self.causes.extend(map(lambda x: (x,False), list(self.config.causes.plural)))
        if self.config.effects == None or len(list(self.config.effects)) == 0:
            self.effects = map(lambda x: x[0], self.causes)
        else:
            self.effects = list(self.config.effects)
        self.phrases = list(self.config.phrases)

    def __enter__(self):
        log.debug("Loading state")
        self.state.load()
        return self

    def __exit__(self, type, value, traceback):
        log.debug("Saving state")
        self.state.save()

    def auth(self):
        """
        Authenticate with twitter.
        """
        log.info("Authenticating...")
        c = self.config.api_keys
        self.api = twitter.Api(consumer_key=c.consumer_key,
                                consumer_secret=c.consumer_secret,
                                access_token_key=c.access_key,
                                access_token_secret=c.access_secret)
        self.creds = self.api.VerifyCredentials()
        log.info("Authenticated as '{}'".format(self.creds.screen_name))
        log.debug("Credentials: {}".format(self.creds))

    def loop(self):
        """
        Loop forever doing stuff.
        """
        log.info("Looping...")

        log.debug("State = {}".format(dict(self.state.d)))

        # set up initial timer for tweets
        if self.config.tweets.enabled:
            self.tweet_timer = self.setup_timer(self.config.tweets, self.state['last_tweet_time'], self.random_tweet)
            self.tweet_timer.start()

        # set up polling timer for mentions
        if self.config.mentions.enabled:
            self.mention_timer = self.setup_timer(self.config.mentions, self.state['last_mention_time'],
                                                  self.check_mentions)
            self.mention_timer.start()

        # set up polling timer for search
        if self.config.search.enabled:
            self.search_timer = self.setup_timer(self.config.search, self.state['last_search_time'],
                                                 self.search_and_reply)
            self.search_timer.start()

        # wait until we're done
        while not self.done:
            time.sleep(1)

    def setup_timer(self, config, last, callback):
        if type(config.timer) == int:
            period = config.timer
        else:
            period = random.randrange(*list(config.timer))

        if last:
            t = time.time() - last
            if t < 0 or t > period:
                t = 0
            else:
                t = period - t
        else:
            t = 0

        log.debug("Returning timer for {} in {} seconds".format(callback, t))

        return Timer(t, callback)

    def terminate(self):
        """
        Stop looping yo.
        """
        log.info("Exiting...")
        self.done = True
        while threading.active_count() > 1:
            if self.tweet_timer:
                self.tweet_timer.cancel()
                self.tweet_timer.join()
            if self.mention_timer:
                self.mention_timer.cancel()
                self.mention_timer.join()
            if self.search_timer:
                self.search_timer.cancel()
                self.search_timer.join()

    def generate(self, cause=None, effect=None, singular=True):
        """
        Generate a new tweet.

        If cause or effect are specified, they will be used as the cause or effect.
        """
        # make sure we have a cause and effect
        if not cause:
            causes = list(self.causes)
            if effect and effect in causes:
                causes.remove(effect)
            cause, singular = causes[random.randrange(0, len(causes))]
        if not effect:
            effects = self.effects
            # wind farms probably don't cause wind farms
            if cause in effects:
                effects = list(effects)
                effects.remove(cause)
            effect = effects[random.randrange(0, len(effects))]

        tweet = "{} cause{} {}".format(cause, 's' if singular else '', effect)

        return tweet

    def tweet(self, *args, **kwargs):
        """
        Generate a status and twoot it.
        """
        t = self.generate(*args, **kwargs)
        log.info("Twooting '{}'".format(t))
        self.api.PostUpdate(t)

    def random_tweet(self):
        """
        Handler for the random tweet timer.

        Generates and tweets a random utterance and then resets the timer.
        """
        log.info("Random tweeting...")
        self.tweet()

        self.state['last_tweet_time'] = time.time()
        self.tweet_timer = self.setup_timer(self.config.tweets, self.state['last_tweet_time'], self.random_tweet)
        self.tweet_timer.start()

    def check_mentions(self):
        """
        Check mentions and reply to them.

        If an error occurs while replying to a mention, that mention will be
        skipped. This includes rate limit errors. Might be worth addressing
        this later, but I don't care about retries at the moment.
        """
        log.info("Checking mentions...")
        try:
            s = self.api.GetMentions(count=self.config.mentions.count, since_id=self.state['last_mention_id'])
            for status in reversed(s):
                reply = "@{} {}".format(status.user.screen_name, self.generate())
                log.info("Replying to mention id {} with {}".format(status.id, reply))
                self.state['last_mention_id'] = status.id

                try:
                    self.api.PostUpdate(reply, in_reply_to_status_id=status.id)
                except twitter.TwitterError as e:
                    log.error("Error occurred while posting mention: {}".format(e))

        except twitter.TwitterError as e:
            log.error("Error occurred while checking mentions: {}".format(e))

        self.state['last_mention_time'] = time.time()
        self.state.save()
        self.mention_timer = self.setup_timer(self.config.mentions, self.state['last_mention_time'], self.check_mentions)
        self.mention_timer.start()

    def search_and_reply(self):
        """
        Search for a term and reply to tweets about it.
        """
        log.info("Performing search...")

        effect = self.effects[random.randrange(0, len(self.effects))]

        try:
            s = self.api.GetSearch(term=effect, count=self.config.search.count, since_id=self.state['last_search_id'])
            for status in reversed(s):
                if status.user.screen_name != self.creds.screen_name:
                    reply = "@{} {}".format(status.user.screen_name, self.generate(effect=effect))
                    log.info("Replying to status id {} with {}".format(status.id, reply))
                    self.state['last_search_id'] = status.id

                    try:
                        self.api.PostUpdate(reply, in_reply_to_status_id=status.id)
                    except twitter.TwitterError as e:
                        log.error("Error occurred while posting mention: {}".format(e))

        except twitter.TwitterError as e:
            log.error("Error occurred while searching: {}".format(e))

        self.state['last_search_time'] = time.time()
        self.state.save()
        self.search_timer = self.setup_timer(self.config.search, self.state['last_search_time'], self.search_and_reply)
        self.search_timer.start()

    def clear(self):
        """
        Clear the timeline.
        """
        for tweet in self.api.GetUserTimeline():
            log.info("Deleting tweet id {}".format(tweet.id))
            self.api.DestroyStatus(tweet.id)