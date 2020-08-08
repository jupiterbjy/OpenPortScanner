## OpenPortScanner

Example Demo (old):
Don't ddos this.  
![Imgur](https://imgur.com/MgitEl7.gif)

Image Shows as if threaded version is lightening-fast, but actually runs same speed with consequent version.  
Python's module 'Socket' blocks when recv is called, rendering all workers other than one useless.  
Asyncio might help, but it's still in WIP.

Still very unstable. Output on windows tend to print 2 lines at one while linux doesn't.  

Only tested for server:client configuration as following: Windows-linux, Windows-Windows.

Trying to create own open-port tester, for use in so-called "Cyber-media, information Room" in ROKA.

There will be 'Examples' Folders from now on to show things I'm struggling with - in case progress is way too slow.

Other repositories without it would have those in PyCharm Scratch folder, not in git.

---

Currently Threading, Consecutive versions of TCP port checkers are working. Example above is threaded version.
