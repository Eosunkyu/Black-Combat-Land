#/bin/bash
#ps -ef | grep uwsgi | awk '{print $2}' | xargs kill -9
ps -ef | grep '[u]wsgi' | awk '{print $2}' | xargs -r kill -9

