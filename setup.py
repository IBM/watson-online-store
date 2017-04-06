# Always prefer setuptools over distutils
from setuptools import setup

long_description = ('Code for Cognitive Developer Journey that uses Watson '
                    'Conversation and Watson Discovery. This application '
                    'demonstrates a simple abstraction of a chatbot '
                    'interacting with a Cloudant NoSQL database, using a '
                    'Slack UI.')

setup(
    name='watson-online-store',
    version='1.0.0',
    description='Demo Retail Chatbot',
    long_description=long_description,
    url='https://github.com/IBM/watson-online-store',
    license='Apache-2.0'
)
