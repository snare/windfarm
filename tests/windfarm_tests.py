from nose.tools import *
import windfarm
from windfarm.bot import WindfarmBot

b = None

def setup():
    global b
    b = WindfarmBot()
    b.auth()

def teardown():
    pass

def test_generate():
    for i in range(10):
        x = b.generate()
        assert 'cause' in x

def test_tweet():
    b.tweet()

def test_clear():
    b.tweet()
    b.clear()
