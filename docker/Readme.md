# GlobaLeaks Docker setup

To run GlobaLeaks using Docker
```bash
 docker run -d --name globaleaks \
  --platform linux/amd64 \
  -p 80:8080 \
  -p 443:8443 \
  -v globaleaks-data:/var/globaleaks \
  --tmpfs /run/globaleaks:uid=1000,gid=1000,mode=0700 \
  globaleaks/globaleaks:latest
```
