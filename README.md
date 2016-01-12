
Prerequisites
=============

* Debian like OS (tested on Ubuntu 15.10)
* Python 2.7
* virtualenvwrapper 4.5.1
* FB Graph API version 2.5

```bash
$ source virtualenvwrapper.sh
```


Project Setup
===================

```bash
$ mkvirtualenv fbcomments-test
$ git clone git@github.com:twil/fbcomments-test.git
$ cd fbcomments-test
./fbcomments-test$ workon fbcomments-test
(fbcomments-test)./fbcomments-test$ pip install -r requirements.txt
```


The Basic Thoughts
==================

1. FB requests are pretty simple - we can use `requests` library.
1. Cursor-based Pagination or Time-based Pagination - this way we can parallelize prosession of comments. Initially we use Cursor-based Pagination and then when we need to update data we will use Time-based Pagination. We need to store the latest post's timestamp though.
1. [Batch Requests](https://developers.facebook.com/docs/graph-api/making-multiple-requests)? might be we can fabricate paged URLs with `offset` and `since`?

