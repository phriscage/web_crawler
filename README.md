web_crawler
=====================

The web crawler application takes a list of URLs as input and extracts all of the image link URLs (gif, jpg, png) as output. The web application crawls the input URLs recursively only to the 2nd path level and adds any additional root URLs to the queue during the first level of crawling. 

I used Flask as the web framework for it's light-weight, simplistic compenents and Elasticsearch for it's distributed, restful storage layer interface. The initial job queue creates a parent document with the URL list and spawns threaded requests to the /crawl method with each URL and parent job_id. Each crawl request first verifies if the URL crawling is already inprogress, then the method adds the URL to the inprogress dictionary and calls the Crawler class. The Crawler class recursively parses the URL html for any image links and then creates a document with the URL and image URLs as the key and values respectively. Finally, the crawl method updates the parent job_id's inprogress and completed dictionaries for the particular URL. Rather than perform a O(N) search for the inprogress and completed status for an URL, I used an empty dictionary for O(1) inserts/deletes. 

The data layer should reside on a separate infrastructure tier and the application deployed behind a load balancer to distribute the threaded/spawned requests. There isn't a limit on the Flask POST request size, so a client can send an unlimited amount of URLs. The runtime would be proprotional to the size of that URL input list, the number of additional URLs parsed on the first level of crawling, the number of child paths for each root URL as well as the size of each of those absolute URLs. The application would require substantial computational and memory resources to handle multiple levels of crawling. 


Quick Start
=====================
```
web_crawler]$ python lib/crawler/api/main.py
2014-12-29 14:13:11,042 INFO werkzeug[1446] : _log :  * Running on http://0.0.0.0:8000/
2014-12-29 14:13:11,043 INFO werkzeug[1446] : _log :  * Restarting with reloader
```

Input
=====================
```
$ curl -X POST -H 'Content-Type: application/json' -d '{"urls: ["http://www.google.com", "http://www.cnn.com"]}' http://127.0.0.1:8000/
{
  "job_id": "jeGB2RgcTvKnrrxSFN8fIA",
  "message": "2 URLs added successfully to 'jeGB2RgcTvKnrrxSFN8fIA'!",
  "success": true
}
```

Status
=====================
```
$ curl -X GET http://127.0.0.1:8000/status/jeGB2RgcTvKnrrxSFN8fIA
{
  "completed": 2,
  "inprogress": 3,
  "success": true
}
```

Result
=====================
```
$ curl -X GET http://127.0.0.1:8000/result/jeGB2RgcTvKnrrxSFN8fIA
{
  "message": "'0' URLs discovered for job_id: 'jeGB2RgcTvKnrrxSFN8fIA'",
  "success": true,
  urls: [
    "http://www.google.com/appsstatus/gwtapp/google.png",
    "http://www.google.com/hangouts/img/logo.png",
    "http://www.google.com/earth/images/products_hl_moon.png",
    "http://www.google.com/images/home/casestudy-khanacademy.png",
...
}
```
