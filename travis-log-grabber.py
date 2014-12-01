#!/usr/bin/python

import os, sys, requests, simplejson, json, codecs
import yaml
from datetime import datetime

## Script to test access to TravisCI logs

class TravisDownloadTest():

    # internal data
    data_dir = "validData"
    github_token = {'github_token': ''}
    header_json_content = {'Content-Type': 'application/json'}
    header_text_content = {'Content-Type': 'text/plain'}
    header_accept = {'Accept': 'application/vnd.travis-ci.2+json'}
    header_accept_plain = {'Accept': 'application/vnd.travis-ci.2+plain'}
    header_accept_text = {'Accept': 'text/plain'}
    header_length = {'Content-Length': 37}
    header_user_agent = {'User-Agent': 'travis-log-grabber/1.0.0'}
    header_auth = {'Authorization': 'token'}
    url_base = "https://api.travis-ci.com"
    url_auth_path = "/auth/github"
    url_base_repo_path = "/repos/"
    log_path = "/logs/"
    travis_token = ""
 

    def __init__(self):
        with open("travis_conf.yaml", 'r') as config_file:
            self.repo_data = yaml.load(config_file)
        
        with open("github.key", 'r') as github_file:
            for line in github_file:
                self.github_token['github_token'] = line.strip()


    # Authenticate uses a github token to request a token from TravisCI
    # The github token can be generated on their site and is loaded from 
    # the file called github.key
    
    def Authenticate(self):
        header_data = {}
        header_data.update(self.header_json_content)
        header_data.update(self.header_accept)
        header_data.update(self.header_length)
        header_data.update(self.header_user_agent)
        data = requests.post(self.url_base + self.url_auth_path, headers=header_data, data=json.dumps(self.github_token))
        
        if data.status_code == 200:
            auth_info = json.loads(data.text)
            self.travis_token = auth_info['access_token']
            self.header_auth['Authorization'] = "%s \"%s\"" % (self.header_auth['Authorization'], self.travis_token)
        else:
            print "Error: %d" % data.status_code
            print data.text

    # The repo_data is loaded from travis_conf.yaml, with the root being the repo name, and
    # each project being a list entry to that repo. This walks that dict and gets the latest
    # job for each and dumps it to a file named after the project.

    def GetRepoBuilds(self):
        for repo, proj_list in self.repo_data.iteritems():
            for project in proj_list:
                print "*******"
                print "Checking %s/%s" % (repo, project)
                print "*******"
                self.GetJobIDs(repo, project)

    # Saves the log file out

    def SaveLog(self, log_text, log_id, project):
        with codecs.open(str(project) + ".log", "w", encoding="utf-8") as log_file:
            log_file.write(log_text)

    # Checks for the latest log ID based on the dates scraped from the job info

    def FindLatestID(self, timestamped_ids):
        latest = datetime(1980, 1, 1)
        latest_id = 0
        
        for key, value in timestamped_ids.iteritems():
            if value > latest:
                latest_id = key
                latest = value
        
        print "Latest id is %d (%s)" % (latest_id, timestamped_ids[latest_id])
        return latest_id

    # Gets the job IDs given the repo/project names

    def GetJobIDs(self, repo, project):
        job_id = 0
        timestamped_ids = {}
        start_time = ""
        finish_time = ""
        header_data = {}
        header_data.update(self.header_json_content)
        header_data.update(self.header_accept)
        header_data.update(self.header_auth)
        header_data.update(self.header_user_agent)

        url_request = self.url_base + self.url_base_repo_path + repo + "/" + project + "/builds"
        data = requests.get(url_request, headers=header_data)
        for key, value in data.json().iteritems():
            if key == "builds":
                print "%d builds found" % len(value)
                for build in value:
                    start_time = ""
                    finish_time = ""
                    for key2, value2 in build.iteritems():
                        if key2 == "job_ids":
                            job_id = value2[0]
                        if key2 == "finished_at":
                            if str(value2) != "None":
                                finish_time = str(value2)
                        if key2 == "started_at":
                            if str(value2) != "None":
                                start_time = str(value2)


                    # add id & timestamp to dict
                    if len(finish_time):
                        timestamped_ids[job_id] = datetime.strptime(str(finish_time), "%Y-%m-%dT%H:%M:%SZ")

                latest_id = self.FindLatestID(timestamped_ids)

                log_id = self.GetLogID(latest_id)
                print "Saving log %d" % log_id
                if not self.GetLog(log_id, project):
                    print "No data found in log, trying archived log"
                    self.GetArchivedLog(latest_id, log_id, project)
                print
                break



    # GetArchivedLog checks for an older log if the log isn't lingering in the current pile on
    # TravisCI.  How do you know?  Well, Travis helpfully returns a blank (which may or may not
    # be a redirect, not sure) when you have a valid job. This routine is run if the regular log
    # fails with the blank record returned.
    #
    # API line below sniffed from TravisCI site (API docs are wrong, jobs/[job_num]/logs doesn't work)
    #
    # https://api.travis-ci.com/jobs/[log_id]/log.txt
    
    def GetArchivedLog(self, job_id, log_id, project):
        header_data = {}
        header_data.update(self.header_user_agent)
        header_data.update(self.header_accept_plain)
        header_data.update(self.header_auth)
        print "Getting log %d for job %d" % (log_id, job_id)
        url_request = self.url_base + "/jobs/" + str(job_id) + "/log.txt"
        print "Requesting: %s" % url_request
        data = requests.get(url_request, headers=header_data)
        if data.status_code == 200:
            if len(data.text.strip()) > 0:
                print "Saving log data"
                data_found = True
                self.SaveLog(data.text, log_id, project)
            else:
                print "No data present in archived log"
        else:
            print "Error: %d" % data.status_code
            print data.text
            print data.headers

    # GetLog checks the regular log API for a log, given a log_id

    def GetLog(self, log_id, project):
        data_found = False
        header_data = {}
        header_data.update(self.header_user_agent)
        header_data.update(self.header_accept_text)
        header_data.update(self.header_auth)
        
        url_request = self.url_base + self.log_path + str(log_id) #+ self.log_path
        data = requests.get(url_request, headers=header_data)
        if data.status_code == 200:
            if len(data.text.strip()) > 0:
                print "Saving log data"
                data_found = True
                self.SaveLog(data.text, log_id, project)
        else:
            print "Error: %d" % data.status_code
            print data.text
    
        return data_found

    # GetLogID finds the log_id for a given job_id

    def GetLogID(self, job_id):
        log_id = 0
        header_data = {}
        header_data.update(self.header_user_agent)
        header_data.update(self.header_accept)
        header_data.update(self.header_auth)
        
        url_request = self.url_base + "/jobs/" + str(job_id)  # + self.log_path
        data = requests.get(url_request, headers=header_data)
        if data.status_code == 200:
            for key, value in data.json().iteritems():
                if key == "job":
                    for key2, value2 in value.iteritems():
                        if key2 == "log_id":
                            print "log_id found: ", value2
                            log_id = int(value2)
        else:
            print "Error: " % data.status_code
            print data.text

        return log_id

# Runs and finds everything
if __name__ == '__main__':
    test = TravisDownloadTest()
    test.Authenticate()
    test.GetRepoBuilds()
