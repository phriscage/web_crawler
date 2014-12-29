web_crawler
=====================

The web crawler application takes a list of URLs as input and extracts all of the image URLs (gif, jpg, png) as output. The web application crawls the input URLs recursively only to the 2nd path level. I choose Flask as the web framework and Elasticsearch as the storage layer. The initial job queue input will spawn threads and call the /crawl method with a given URL and job_id for each URL in the payload. 


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
$ curl -X POST -H 'Content-Type: application/json' -d '{"urls: ["http://www.docker.com", "http://www.cnn.com"]}' http://127.0.0.1:8000/
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
  "urls": []
}
```
