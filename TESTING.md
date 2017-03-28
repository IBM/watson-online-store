Testing Guide
=============

This document describes how to run style and unit tests for our repository.
Please ensure these tests are run before proposing new code.

Running Style and Unit Tests
----------------------------

Since the code for this repository is written in Python, we make use of
[virtualenv](http://virtualenvwrapper.readthedocs.io/) for running tests.

```
# Create virtual environment
$ virtualenv ~/wos

# Activate virtual environment
$ source ~/wos/bin/activate

# Install pre requisites
$ pip install -r requirements.txt
$ pip install -r test-requirements.txt
$ pip install flake8

Run style tests
$ flake8 .

Run unit tests
$ py.test --cov=watsononlinestore
```

