
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
=============

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
1. Cursor-based Pagination or Time-based Pagination (not working with comments edge!) - this way we can parallelize prosession of comments. Initially we use Cursor-based Pagination and then when we need to update data we will use Time-based Pagination. We need to store the latest post's timestamp though.
1. [Batch Requests](https://developers.facebook.com/docs/graph-api/making-multiple-requests)? might be we can fabricate paged URLs with `offset` and `since`?
1. Error procession. If response (JSON) has `error` property then request failed.
1. [Rate limiting](https://developers.facebook.com/docs/graph-api/advanced/rate-limiting). App Level Throttling: 200 calls/person/hour (Error Code 4).
1. Don't request unneeded fields (we need only `created_time` to calculate the frequency of comments).
1. [Timeouts](https://developers.facebook.com/docs/graph-api/making-multiple-requests#timeouts).
1. Use `multiprocessing`
1. Use Google Charts
1. `pandas` has a very neat way for calculating needed frequencies `Series.resample('3Min', how='sum', label='right')`. But how to parallelize the whole thing?
1. The last index after `Series.resample()` of one page will be the same as the first one of the next page. In this case we need to sum these values to merge two sequences. If per chance the first index of the second page is different then we need to concatenate two sequences and that's it!
1. **How to parallelize?** We get pages from FB sequentially. We can only parallelize procession of received data:(

So we have ~52k comments for the given post (10151775534413086) and 200 requests per hour per user and a limit of 5k comments in a single request (it might be less?).

We need 11 requests to procession the data.

52k comments in 5 minute buckets are 257k timestamps! We can drop NA values. That'll give ~4k values.


Zero Approximation
==================

1. Get an Access Token somehow (out of scope at this moment)
1. Get all the comments timestamps using Cursor-based pagination with 10k limit and selecting only `created_time` field
1. Calculate the frequencies for 5 min intervals
1. Create a report folder
1. Save data `data.json`
1. Copy template `report.html` into the report folder


Errors Procession
=================

Codes to wait and retry:
* 1 - API Unknown. Retry and forget if not successful.
* 2 - API Service.
* 4 - API Too Many Calls. Examine your API request volume?
* 17 - API User Too Many Calls. Examine your API request volume?
* 341 - Application limit reached. Examine your API request volume?


How To Get Access Token
=======================

With JS
-------

In Chrome Dev Tools (app is configured for `test.domain` domain)

```javascript
// test.domain
window.fbAsyncInit = function() {
  FB.init({
    appId      : '645041415635369',
    xfbml      : true,
    version    : 'v2.5'
  });
};

(function(d, s, id){
 var js, fjs = d.getElementsByTagName(s)[0];
 if (d.getElementById(id)) {return;}
 js = d.createElement(s); js.id = id;
 js.src = "//connect.facebook.net/en_US/sdk.js";
 fjs.parentNode.insertBefore(js, fjs);
}(document, 'script', 'facebook-jssdk'));

FB.login(function(){}, {scope: ''});

FB.getAuthResponse();
```

Desktop (without JS)
--------------------

```
https://www.facebook.com/dialog/oauth?client_id=645041415635369&redirect_uri=https://www.facebook.com/connect/login_success.html&response_type=token
```

After confirmation of permissions you'll be redirected to a new URL with `access_token` in it.

Device (a.k.a. TV)
------------------

https://developers.facebook.com/docs/facebook-login/for-devices

Server-to-Server Request
------------------------

Somehow with an App Secret or Client Token.



Check The `limit` For The `/comments` Edge of The `/post` Node
==============================================================


```javascript
FB.api(
  '/10151775534413086/comments',
  'GET',
  {"fields":"created_time","limit":"100000","pretty":"0","summary":"1","filter":"stream"},
  function(response) {
      console.log(response.data.length);
  }
);
```

This will give us `5000`
