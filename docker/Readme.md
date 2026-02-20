# GlobaLeaks Docker setup

To run GlobaLeaks using Docker
```bash
 docker run -d --name globaleaks \
  --platform linux/amd64 \
  -p 80:8080 \
  -p 443:8443 \
  -v globaleaks-data:/var/globaleaks \
  globaleaks/globaleaks:latest
