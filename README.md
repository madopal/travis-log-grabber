travis-log-grabber
==================

Grabs logs from TravisCI using the API, and repos specified in yaml config file. A key from github is necessary in the github.key file, which can be generated according to:

https://help.github.com/articles/creating-an-access-token-for-command-line-use/

Also, the yaml config expects organizations and repositories like:

ORG1:
  - repo1
  - repo2
ORG2:
  - repo3


