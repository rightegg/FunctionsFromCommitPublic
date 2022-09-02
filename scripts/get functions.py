from calendar import c
import numpy as np
import pandas as pd
import os
import sys
import string
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from bs4 import BeautifulSoup
import time
import datetime
import ssl
import numpy as np
import pandas as pd
import traceback
import csv
ssl._create_default_https_context = ssl._create_unverified_context
import json
import subprocess
import glob
import requests
from pprint import pprint
from difflib import Differ
from pathlib import Path
import pandas

# find all the line numbers that the functions begins
def get_line_numbers(filename):
    print("getting line numbers for " + filename)
    pos = filename.rfind('.') #position of last period
    lang_type = filename[pos+1:] #language of file
    if lang_type in ["C","cc","cxx","cpp","c++","Cpp"]:
        lang_type = "c++"
    if (lang_type == "h"):
        lang_type = "c"
    if (lang_type != "c++" and lang_type != "c"):
        print(lang_type)
        return [], -1
    # found = False
    #cmd = "ctags -x --c-kinds=fp " + filename + " | grep " + funcname
    cmd = "ctags -x --"+lang_type+"-kinds=f " + filename

    output = subprocess.getoutput(cmd)
    lines = output.splitlines()
    line_nums = []
    for line in lines:
        line = line.split(" ")
        char = list(filter(None, line))
        line_num = char[2]
        line_nums.append(int(line_num))
    return line_nums, 0

def get_diff_lines(filename):
    diff_lines = []
    with open(filename, "r") as f:
        for i, line in enumerate(f):
            if line.startswith("+") or line.startswith("-"):
                diff_lines.append(i)
    return diff_lines

#get code of function starting at line number
def process_file(filename, line_num):
    print("opening " + filename + " on line " + str(line_num))

    code = ""
    cnt_braket = 0
    found_start = False
    found_end = False

    with open(filename, "r") as f:
        for i, line in enumerate(f):
            if(i >= (line_num - 1)):
                code += line

                if (not line.startswith("//")) and line.count("{") > 0:
                    found_start = True
                    cnt_braket += line.count("{")

                if (not line.startswith("//")) and line.count("}") > 0:
                    cnt_braket -= line.count("}")

                if cnt_braket == 0 and found_start == True:
                    found_end = True
                    return code, i+1
    if (found_end == False):
        return "did not find end", -1

def getDiffFromCommit(sha, tries=0): #returns 0 for success, -1 for failure
    try:
        curpath = os.path.abspath(os.curdir)
        print("getting diff for " + sha)

        #get new file
        url = f"https://api.github.com/search/commits?q=" + sha
        d = Differ() #create differ
        ratelimited = False
        while True:
            searchquery = requests.get(url, 
                headers={
                    'Authorization': Enter Authorization Here
                }
            ).json()
            if ('message' in searchquery):
                if (searchquery['message'] == 'API rate limit exceeded for 73.140.54.71. (But here\'s the good news: Authenticated requests get a higher rate limit. Check out the documentation for more details.)'):
                    ratelimited = True
                    print("rate limited, waiting 10 minutes")
                    for elapsed in range(0, 600, 1):
                        sys.stdout.write("\r")
                        sys.stdout.write("{:2d} seconds of 600 elapsed.".format(elapsed))
                        sys.stdout.flush()
                        time.sleep(1)
                else:
                    ratelimited = False
            else:
                ratelimited = False
            
            if (ratelimited == False):
                break
                
            
        commit_url = searchquery["items"][0]["url"]
        commit = requests.get(commit_url, 
            headers={
                'Authorization': Enter Authorization Here
            }
            ).json()
        print("HERE------------------------------------")
        old_commit_sha = commit["parents"][0]["sha"] #sha of parent
        num_changed_files = len(commit["files"]) #number of files changed in commit
        for i in range(num_changed_files):
            #get new file
            raw_url = commit["files"][i]["raw_url"]
            pos = raw_url.rfind('.') #position of last period
            lang = raw_url[pos+1:] #language of file
            new_file = requests.get(raw_url).text #postcommit in string format
            with open(os.path.join(curpath, "temp_files\\new_file" + str(i) + "." + lang), "w", encoding="utf-8") as new_file_temp: #save postcommit file
               new_file_temp.write(new_file)

            #get old file
            old_raw_url = raw_url.replace(sha, old_commit_sha)
            old_file = requests.get(old_raw_url).text #precommit file in string format
            with open(os.path.join(curpath, "temp_files\old_file" + str(i) + "." + lang), "w", encoding="utf-8") as old_file_temp: #save precommit file
                old_file_temp.write(old_file)

            #diff the files

            with open (os.path.join(curpath, "temp_files\old_file" + str(i) + "." + lang), encoding="utf-8") as f:
                file1_lines = f.readlines()
            with open (os.path.join(curpath, "temp_files\\new_file" + str(i) + "." + lang), encoding="utf-8") as f:
                file2_lines = f.readlines()
            difference = list(d.compare(file1_lines, file2_lines))
            difference = '\n'.join(difference)
            with open(os.path.join(curpath, "diff_files\diff" + str(i) + "." + lang), "w", encoding="utf-8") as diff_file:
                diff_file.write(difference)

        return 0, ""
    except HTTPError as e:
        if e.code == 429:
            if (tries >= 5):
                print("429 please wait")
                print(url)
                return -1, "429"
            else:
                time.sleep(10)
                print("429 error")
                return getDiffFromCommit(sha, tries+1)
        if e.code == 404:
            print("\n not found:" + url+ "！")
            return -1, "404"
        if e.code == 403:
            if (tries >= 5):
                print("403 please wait")
                print(url)
                return -1, "403"
            else:
                time.sleep(10)
                print("403 error")
                return getDiffFromCommit(sha, tries+1)
        raise
    except Exception as e:
        print("reason", e)
        print("\n skip get_response:"+sha+ "！")
            

def main():
    curpath = os.path.abspath(os.curdir)
    logdir = os.path.join(curpath, "Logs")
    log = open(os.path.join(logdir, "function_grabbing_log.txt"), "w")
    commit_list = pandas.read_csv(os.path.join(curpath, "data/commits.csv"))
    error_output_list = open(os.path.join(curpath, "output/errorCommits.csv"), "w", encoding='UTF8')
    error_writer=csv.writer(error_output_list)
    error_writer.writerow(['CWE ID', "commit ID", "filenum", "reason"])

    with open(os.path.join(curpath, "output/output.csv"), "w", encoding='UTF8') as output:
        writer = csv.writer(output)
        writer.writerow(['CWE ID', 'commit ID', 'func_before', 'processed_func', 'vul_func_with_fix'])

        for index, row in commit_list.iterrows():
            try:
                commitID = row["commit ID"]
                if (commitID == "" or commitID == "nan"):
                    continue
                CWEID = row["CWE ID"]
                if (CWEID == ""):
                    error_writer.writerow(["",commitID,"", "no CWE id"])
                    continue
                result, errormsg = getDiffFromCommit(commitID)
                if (result == 0):
                    diffdir = os.path.join(curpath, "diff_files")

                    filenum = 0
                    for filename in os.listdir(diffdir):
                        f = os.path.join(diffdir, filename)
                        # checking if it is a file
                        if os.path.isfile(f):
                            pos = f.rfind('.') #position of last period
                            lang = f[pos+1:] #language of file            
                            #get function line numbers in diff
                            func_line_nums, msg = get_line_numbers(f)
                            if (msg == -1):
                                error_writer.writerow([CWEID, commitID, filenum, "unknown language"])
                                print("unknown language")
                                filenum += 1
                                continue
                            func_line_nums.sort()
                            #get function line numbers in precommit file
                            print("oldfile lang " + lang)
                            print(filenum)
                            oldfile = os.path.join(curpath, "temp_files\old_file" + str(filenum) + "." + lang)
                            old_func_line_nums, msg = get_line_numbers(oldfile)
                            if (msg == -1):
                                error_writer.writerow([CWEID, commitID, filenum, "unknown language"])
                                filenum += 1
                                continue
                            old_func_line_nums.sort()
                            print(old_func_line_nums)
                            #get function line numbers in postcommit file
                            newfile = os.path.join(curpath, "temp_files\\new_file" + str(filenum) + "." + lang)
                            new_func_line_nums, msg = get_line_numbers(newfile)
                            if (msg == -1):
                                error_writer.writerow([CWEID, commitID, filenum, "unknown language"])
                                filenum += 1
                                continue
                            new_func_line_nums.sort()


                            #if the number of functions between the old and new file are different
                            #some functions are added/removed instead of simply replaced
                            #which requires more work, and will be put aside for later.
                            if (len(new_func_line_nums) != len(old_func_line_nums)):
                                log.write("commit has changed the number of functions: " + commitID + "\n")
                                error_writer.writerow([CWEID, commitID, filenum, "changed num of functions"])
                                filenum += 1
                                continue

                            #get diff line numbers
                            diff_lines = get_diff_lines(f)

                            #get changed functions
                            changed_funcs_lines = []
                            changed_funcs_index = []
                            i=0
                            j=0
                            while (i<len(func_line_nums)-1 and j<len(diff_lines)):
                                if ((diff_lines[j] < func_line_nums[i+1] and diff_lines[j] > func_line_nums[i]) or diff_lines[j] == func_line_nums[i]):
                                    changed_funcs_lines.append(func_line_nums[i])
                                    changed_funcs_index.append(i)
                                    i+=1
                                    j+=1
                                elif (diff_lines[j] < func_line_nums[i]):
                                    j+=1
                                elif (diff_lines[j] > func_line_nums[i]):
                                    i+=1

                            if (len(changed_funcs_lines) == 0):
                                log.write("no functions were changed in commit: " + commitID)
                                error_writer.writerow([CWEID, commitID, filenum, "no functions changed"])
                                filenum += 1
                                continue

                            #replace + and - in function
                            func_num = 0
                            for func_line in changed_funcs_lines:
                                #get function code
                                code, end_num = process_file(f, func_line)
                                print("opened diff file")
                                #write it to a temp file
                                with open(os.path.join(curpath, "temp_files/temp_changed_func.txt"), "w") as temp:
                                    temp.write(code)

                                #replace the lines
                                with open(os.path.join(curpath, "temp_files/temp_changed_func.txt"), "r") as temp:
                                    #write to new file
                                    with open(os.path.join(curpath, "temp_files/temp_changed_func_edited.txt"), "w") as temp_changed:
                                        #get code lines of original function
                                        for i,line in enumerate(temp):
                                            #check if code is empty
                                            if (line != "+ \n" and line != "- \n"):
                                                #replace code
                                                if line.startswith("+"):
                                                    line = line.replace("+","//fix_flaw_line_below:\n//",1)
                                                if line.startswith("-"):
                                                    line = line.replace("-","//flaw_line_below:\n",1)
                                                if line.startswith("?"):
                                                    continue
                                                if not code.endswith("\n"):
                                                    line = line + "\n"
                                                #output to new file
                                                temp_changed.write(line)

                                #read edited file
                                with open(os.path.join(curpath, "temp_files/temp_changed_func_edited.txt"), "r") as temp_changed:
                                    edited_code = temp_changed.read() #vul_func_with_fix

                                print("getting function number " + str(func_num))
                                #get func_before
                                print(oldfile)
                                print(old_func_line_nums)
                                func_before, i = process_file(oldfile, old_func_line_nums[changed_funcs_index[func_num]])

                                #get func_after/processed_func
                                func_after, i = process_file(newfile, new_func_line_nums[changed_funcs_index[func_num]])
                                
                                #write to csv
                                writer.writerow([CWEID, commitID, func_before, func_after, edited_code])

                                func_num += 1
                            filenum += 1
                elif (result == -1):
                    log.write("error retriving commit info for ID: " + commitID + " because of " + str(errormsg) + "\n")
                    error_writer.writerow([CWEID, commitID, "", errormsg])
            except Exception as e:
                print(str(e))
                error_writer.writerow([CWEID, commitID, "", str(e)])
    
    log.close()

if __name__ == "__main__":
    main()