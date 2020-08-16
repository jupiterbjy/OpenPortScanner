## OpenPortScanner

Example Demo (old):
Don't ddos this.  
![Imgur](https://imgur.com/MgitEl7.gif)

Image Shows as if threaded version is lightening-fast, but actually runs same speed with consequent version.  
Python's module 'Socket' blocks when recv is called, rendering all workers other than one useless.  

Asyncio version runs way faster, but not sure if socket connection is actually running asynchronously or not.  
Anyhow, this personal repo was worth trying as now I learned how to play with threading and asyncio.

Trying to create own open-port tester, for use in so-called "Cyber-media, information Room" in ROKA.

There will be 'Examples' Folders from now on to show things I'm struggling with - in case progress is way too slow.

---

Currently Threading, Consecutive, asyncio versions of TCP port checkers are working. Example above is threaded version.
