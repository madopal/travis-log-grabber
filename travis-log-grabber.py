#!/usr/bin/python

import os, sys
import requests
import simplejson, json
import codecs
import xlwt
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

    all_logs = {}

    test_results = {
        'signpost': ["ok", "fail"],
        'psqlgraph': ["ok", "fail"],
        'gdcapi': ["PASSED", "FAILED"],
        'portal-ui': ["PASSED", "FAILED"],
        'master': ["PASSED", "FAILED"]
    }

    issue_list = {
        'signpost': ["GDC-156"],
        'psqlgraph': ["GDC-152"],
        'gdcapi': ["GDC-158"],
        'portal-ui': ["OICR"],
    }

    def __init__(self):
        with open("travis_conf.yaml", 'r') as config_file:
            self.repo_data = yaml.load(config_file)
        
        with open("github.key", 'r') as github_file:
            for line in github_file:
                self.github_token['github_token'] = line.strip()


    #
    # Parsing routines for different test/log types
    # regexes would be better in here when there is time
    #

    # parse_nose_tests - parses tests run with nose

    def parse_nose_tests(self, log_data):
        print "nose test file, %d lines in log data" % len(log_data)
        tests = {}
        test_lines = False
        passes = 0
        fails = 0
        for line in log_data:
            if test_lines:
                if line.find("...") != -1:
                    line_parts = line.split("...")
                    if line_parts[1].strip().find("ok") != -1:
                        test_type = line_parts[0].strip()
                        if test_type in tests:
                            test_type = test_type + "_"
                        tests[test_type] = self.test_results['master'][0]
                        passes = passes + 1
                        print "%d: %s - %s" % (passes, test_type, tests[line_parts[0].strip()])
                    else:
                        test_type = line_parts[0].strip()
                        if test_type in tests:
                            test_type = test_type + "_"
                        tests[test_type] = self.test_results['master'][1]
                        fails = fails + 1
                        print "%d: %s - %s" % (fails, test_type, tests[line_parts[0].strip()])
                else:
                    if line.find("-----------------") != -1:
                        test_lines = False

            else:
                if line.find("nosetests") != -1:
                    test_lines = True

        print "%d pass, %d fail, %d total" % (passes, fails, passes + fails)
        print "%d items in dict" % len(tests)
        tests['totals'] = [passes, fails]
        return tests

    # parse_py_test - parses tests run with py.test

    def parse_py_test(self, log_data):
        print "py.test file, %d lines in data" % len(log_data)
        tests = {}
        test_lines = False
        unmatched_line = False
        passes = 0
        fails = 0
        test_type = ""
        for line in log_data:
            if test_lines:
    #            print line
                if line.find("PASSED") != -1:
                    if not unmatched_line:
                        line_parts = line.split("[32m")
                        test_type = line_parts[0].split("::")[1].strip()
                        test_type = test_type.split()[0]
                    else:
                        unmatched_line = False
                    if test_type in tests:
                        test_type = test_type + "_"
                    tests[test_type] = self.test_results['master'][0]
                    passes = passes + 1
                    print "%d: %s - %s" % (passes, test_type, tests[test_type])
                elif line.find("FAILED") != -1:
                    if not unmatched_line:
                        line_parts = line.split("[31m")
                        test_type = line_parts[0].split("::")[1].strip()
                        test_type = test_type.split()[0]
                    else:
                        unmatched_line = False
                        
                    if test_type in tests:
                        test_type = test_type + "_"
                    tests[test_type] = self.test_results['master'][1]
                    fails = fails + 1
                    print "%d: %s - %s" % (fails, test_type, tests[test_type])
                elif line.find("FAILURES") != -1:
                    test_lines = False
                else:
                    print "Line w/o results"
                    if line.find("::") != -1:
                        test_type = line.split("::")[1].strip()
                        test_type = test_type.split()[0]
                    else:
                        test_type = "unknown test"
                    unmatched_line = True

            else:
                if line.find("test session starts") != -1:
                    test_lines = True

        print "%d pass, %d fail, %d total" % (passes, fails, passes + fails)
        print "%d items in dict" % len(tests)
        tests['totals'] = [passes, fails]

        return tests

    # parse_npm_test - parses tests run with npm

    def parse_npm_test(self, log_data):
        print "NPM test script, %d lines in data" % len(log_data)
        tests = {}
        test_lines = False
        passes = 0
        fails = 0
        for line in log_data:
            if test_lines:
                if line.find("[32m") != -1:
                    line_parts = line.split("[32m")
                    test_type = line_parts[-1].strip().strip("[39m")
                    if len(test_type):
                        if test_type in tests:
                            test_type = test_type + "_"
                        tests[test_type] = self.test_results['master'][0]
                        passes = passes + 1
                        print "%d: %s - %s" % (passes, test_type, tests[test_type])
                elif line.find("[31m") != -1:
                    line_parts = line.split("[31m")
                    test_type = line_parts[-1].strip().strip("[39m")
                    if len(test_type):
                        if test_type in tests:
                            test_type = test_type + "_"
                        tests[test_type] = self.test_results['master'][1]
                        fails = fails + 1
                        print "%d: %s - %s" % (fails, test_type, tests[test_type])
                if line.find("SUMMARY:") != -1:
                    test_lines = False

            else:
                if line.find("Start:") != -1:
                    test_lines = True
        
        print "%d pass, %d fail, %d total" % (passes, fails, passes + fails)
        print "%d items in dict" % len(tests)
        tests['totals'] = [passes, fails]
        return tests


    # list of callback to test type

    test_routines = {   
        'signpost': parse_nose_tests,
        'psqlgraph': parse_nose_tests,
        'gdcapi': parse_py_test,
        'portal-ui': parse_npm_test
    }


    # authenticate uses a github token to request a token from TravisCI
    # The github token can be generated on their site and is loaded from 
    # the file called github.key
    
    def authenticate(self):
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
            sys.exit()


    # The repo_data is loaded from travis_conf.yaml, with the root being the repo name, and
    # each project being a list entry to that repo. This walks that dict and gets the latest
    # job for each and dumps it to a file named after the project.

    def get_repo_builds(self):
        for repo, proj_list in self.repo_data.iteritems():
            for project in proj_list:
                print "*******"
                print "Checking %s/%s" % (repo, project)
                print "*******"
                self.get_job_ids(repo, project)


    # Saves the log file out, as well as adds the log body to a dict to be processed later, if need be

    def save_log(self, log_text, log_id, project, started_time):
        with codecs.open(str(project) + ".log", "w", encoding="utf-8") as log_file:
            log_file.write(log_text)

        self.all_logs[project] = { 'data': log_text.split('\n'), 'date': started_time }


    # Checks for the latest log ID based on the dates scraped from the job info

    def find_latest_id(self, timestamped_ids):
        latest = datetime(1980, 1, 1)
        latest_id = 0

        for key, value in timestamped_ids.iteritems():
            if value > latest:
                latest_id = key
                latest = value

        print "Latest id is %d (%s)" % (latest_id, timestamped_ids[latest_id])
        return latest_id


    # Gets the job IDs given the repo/project names

    def get_job_ids(self, repo, project):
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

                latest_id = self.find_latest_id(timestamped_ids)

                log_id = self.get_log_id(latest_id)
                print "Saving log %d" % log_id
                if not self.get_log(log_id, project, timestamped_ids[latest_id]):
                    print "No data found in log, trying archived log"
                    self.get_archived_log(latest_id, log_id, project, timestamped_ids[latest_id])
                print
                break



    # get_archived_log checks for an older log if the log isn't lingering in the current pile on
    # TravisCI.  How do you know?  Well, Travis helpfully returns a blank (which may or may not
    # be a redirect, not sure) when you have a valid job. This routine is run if the regular log
    # fails with the blank record returned.
    #
    # API line below sniffed from TravisCI site (API docs are wrong, jobs/[job_num]/logs doesn't work)
    #
    # https://api.travis-ci.com/jobs/[log_id]/log.txt

    def get_archived_log(self, job_id, log_id, project, started_time):
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
                self.save_log(data.text, log_id, project, started_time)
            else:
                print "No data present in archived log"
        else:
            print "Error: %d" % data.status_code
            print data.text
            print data.headers


    # get_log checks the regular log API for a log, given a log_id

    def get_log(self, log_id, project, started_time):
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
                self.save_log(data.text, log_id, project, started_time)
        else:
            print "Error: %d" % data.status_code
            print data.text

        return data_found


    # get_log_id finds the log_id for a given job_id

    def get_log_id(self, job_id):
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


    # output_results checks the log data, parses it, and spits out a spreadsheet and a JSON file

    def output_results(self):

        overall_data = {}
        json_data = {'issues': []}

        # walks the log data so far and calls the appropriate parse routines
        for key, log_data in self.all_logs.iteritems():
            for type, routine in self.test_routines.iteritems():
                if key == type:
                    data = routine(self, log_data['data'])
                    overall_data[type] = {'data': data, 'date': log_data['date']}


        # create the spreadsheet, spreadsheet filename, and first sheet
        wb = xlwt.Workbook()
        main_sheet = wb.add_sheet('Issues')
        run_time = datetime.utcnow()
        sheet_filename = "testResults_%04d-%02d-%02d.xls" % (run_time.year, run_time.month, run_time.day)

        # write the header line with the style
        header_style = xlwt.easyxf('font: bold on;font: italic on;font: underline on')

        main_sheet.write(0, 0, "Issue", header_style)
        main_sheet.write(0, 1, "Work", header_style)
        main_sheet.write(0, 2, "Test Status", header_style)
        main_sheet.write(0, 3, "Work Type", header_style)
        main_sheet.write(0, 4, "Test Date", header_style)

        cur_row = 1

        json_file = open("test_result.json", "w")
        longest_date_str = 0

        # parse all the data into the spreadsheet/JSON doc
        for key, value in overall_data.iteritems():

            issue_data = {}

            issue_data['name'] = key
            issue_data['JIRA issue'] = self.issue_list[key][0]
            issue_data['JIRA url'] = "https://jira.opensciencedatacloud.org/browse/%s" % self.issue_list[key][0]

            # set up hyperlinks in the spreadsheet
            jira_link = 'HYPERLINK("https://jira.opensciencedatacloud.org/browse/%s";"%s")' % (self.issue_list[key][0], self.issue_list[key][0])
            main_sheet.write(cur_row, 0, xlwt.Formula(jira_link))
            sheet_link = 'HYPERLINK("#%s!A1";"%s")' % (key, key)
            main_sheet.write(cur_row, 1, xlwt.Formula(sheet_link))
            cur_data = value['data']

            issue_data['detailed results'] = cur_data

            # set results as the strings in 'master'
            if cur_data['totals'][1] == 0:
                result = self.test_results['master'][0]
            else:
                result = self.test_results['master'][1]

            issue_data['result'] = "%s (%d/%d)" % (result, cur_data['totals'][0], cur_data['totals'][0] + cur_data['totals'][1])
            issue_data['test type'] = "unit test"
            issue_data['timestamp'] = "%s" % value['date']

            print "%s: %d(%d) tests, pass/fail = %d/%d, result = %s" % (key, cur_data['totals'][0] + cur_data['totals'][1], len(cur_data) - 1, cur_data['totals'][0], cur_data['totals'][1], result)
            main_sheet.write(cur_row, 2, result)

            # resize the test column to the widest test string
            date_completed = "%s" % value['date']
            if len(date_completed) > longest_date_str:
                longest_date_str = len(date_completed)
            main_sheet.write(cur_row, 4, date_completed)
            cur_row = cur_row + 1

            # write the details for each test to a sheet
            temp_sheet = wb.add_sheet(key)
            temp_sheet.write(0, 0, "Test", header_style)
            temp_sheet.write(0, 1, "Result", header_style)
            temp_row = 1
            longest_str = 0
            for key2, value2 in cur_data.iteritems():
                if key2 != 'totals':
                    temp_sheet.write(temp_row, 0, key2)
                    temp_sheet.write(temp_row, 1, value2)
                    temp_row = temp_row + 1
                    if len(key2) > longest_str:
                        longest_str = len(key2)

            # set the column width to the longest string (approx)
            second_col_width = temp_sheet.col(0)
            second_col_width.width = 254 * longest_str

            # write out the top level json
            json_data['issues'].append(dict(issue_data))


        json_data['timestamp'] = "%04d-%02d-%02d %02d:%02d:%02d" % (run_time.year, run_time.month, run_time.day, run_time.hour, run_time.minute, run_time.second)
        # resize the date column to the widest date string
        date_col_width = main_sheet.col(4)
        date_col_width.width = 254 * longest_date_str

        # save out the spreadsheet and the json
        wb.save(sheet_filename)

        # write json to file
#        print json.dumps(json_data, indent=4, sort_keys=True)
        simplejson.dump(json_data, json_file)
        json_file.close()


# Runs and finds everything
if __name__ == '__main__':
    test = TravisDownloadTest()
    test.authenticate()
    test.get_repo_builds()
    test.output_results()
