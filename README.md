## OpenPortScanner

Example Demo (old):
Don't ddos this.  
![Imgur](https://imgur.com/MgitEl7.gif)

Image Shows as if threaded version is lightening-fast, but actually runs same speed with consequent version.  
Python's module 'Socket' blocks when recv is called, rendering all workers other than one useless.  
Same goes for asyncio, despite wasting ton of time on it. Currently this repository is almost scraped - but was worth as now I learned how to play with threading and asyncio.

Trying to create own open-port tester, for use in so-called "Cyber-media, information Room" in ROKA.

There will be 'Examples' Folders from now on to show things I'm struggling with - in case progress is way too slow.

Other repositories without it would have those in PyCharm Scratch folder, not in git.

---

Currently Threading, Consecutive versions of TCP port checkers are working. Example above is threaded version.
