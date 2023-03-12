from __future__ import print_function

from apiclient import discovery
from httplib2 import Http
from oauth2client import client, file, tools
import pandas as pd
import numpy as np
import os
import zipfile
import re


SCOPES = "https://www.googleapis.com/auth/forms.body"
DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"

store = file.Storage('token.json')
creds = None
form_service = None


def load_student_info(filename):
    """
    Loads student info from a csv file.
    student info is a list with [{idx: student idx, andrewid: student andrewid}]
    """
    df = pd.read_csv(filename)
    student_info = []
    for _, row in df.iterrows():
        student_info.append(
            {"idx": row["idx"], "andrewid": row["andrewid"], "name": row["name"]})
        if "url" in row:
            student_info[-1]["url"] = row["url"]
    return student_info


def unzip_submissions(student_info):
    """
    Unzips the submissions for each student.
    each submission is a zip file in the format Random-string-{andrewid}.zip in submissions/
    student info is a dict with {student idx: student andrewid}
    """
    id_to_idx = {s["andrewid"]: s["idx"] for s in student_info}
    # read in all zip files in submissions/
    for f in os.listdir("submissions/"):
        if f.endswith(".zip"):
            # unzip the file
            with zipfile.ZipFile("submissions/" + f, 'r') as zip_ref:
                andrewid = f[:-4].split("-")[-1]
                idx = id_to_idx[andrewid]
                zip_ref.extractall(f"submissions/{idx}-{andrewid}")
            # remove the zip file
            os.remove("submissions/" + f)


def create_gforms(student_info, title):
    for student in student_info:
        idx, andrewid = student["idx"], student["andrewid"]
        try:
            url = create_one_gform(idx, andrewid, title)
            student["url"] = url
        except Exception as e:
            print(f"Error creating form for {idx}-{andrewid}: {e}")
            student["url"] = "(Missing)"
        # break
    # write it to student info
    df = pd.DataFrame(student_info)
    df.to_csv("student_info.csv", index=False)
    return student_info


def create_one_gform(idx, andrewid, title):
    """
    Creates a Google Form for one student's grading. 
    index is the student's index in the student_info dict
    andrewid is the student's andrewid
    Returns the form url.
    Read the .md file, parse it and create a Google Form for each student.
    """
    global form_service
    global creds
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_secrets.json', SCOPES)
        creds = tools.run_flow(flow, store)

        form_service = discovery.build('forms', 'v1', http=creds.authorize(
            Http()), discoveryServiceUrl=DISCOVERY_DOC, static_discovery=False)

    def clean_markdown_format(text):
        """
        Cleans up the markdown format for the question.
        """
        # text = text.replace("###", "")
        text = text.replace("*", "")
        text = re.sub(r"\n\n+", "\n\n", text)
        #text = re.sub(r"^\\t+-", "-", text)
        #text = re.sub(r"^\s+-", "-", text)
        #text = re.sub(r"^-", "    -", text)
        return text

    # read the .md file
    for f in os.listdir(f"submissions/{idx}-{andrewid}/"):
        if f.endswith(".md"):
            with open(f"submissions/{idx}-{andrewid}/{f}", "r") as f:
                md = f.read()
                break
    # parse the .md file
    md = "## Task Summary\n\n" + md.split("## Task Summary")[1]
    description, tests = md.split("## Test Summary")
    tests = re.split("### Test [0-9]+:", tests)[1:]

    # Request body for creating a form
    with open("grade_instruction.txt", "r") as f:
        general_instruction = f.read()
    NEW_FORM = {
        "info": {
            "title": f"{title} - #{idx}",
            "documentTitle": f"{title}-{idx}-{andrewid}",
        }
    }

    NEW_QUESTIONS = {
        "includeFormInResponse": True,
        "requests": [
            {
                "updateFormInfo": {
                    "info": {
                        "description": general_instruction
                    },
                    "updateMask": "description"

                }
            }
        ]}

    # add the description
    NEW_QUESTIONS["requests"].append({
        "createItem": {
            "item": {
                "title": "I have read and understood the task and model description.",
                "description": clean_markdown_format(description),
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "RADIO",
                            "options": [
                                {"value": "Yes"},
                            ],
                        }
                    }
                },
            },
            "location": {
                "index": 0
            }
        }
    })

    # add the tests
    for id, test in enumerate(tests):
        test = clean_markdown_format(test)
        if test:
            test = f"Test {id + 1}: {test}"
            title = test.split('\n')[0]
            NEW_QUESTIONS["requests"].append({
                "createItem": {
                    "item": {
                        "title": f"Rating: [{title}]. Do you think this test has exposed a severe model bug?",
                        "description": f"----\n\n {test} \n\n---\n",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": [
                                        {"value": "1: The model does not fail on this test enough for me to consider it a bug."},
                                        {"value": "2: It fails enough that I think this is a minor bug."},
                                        {"value": "3: This is a bug that is worth investigating and fixing."},
                                        {"value": "4: This is a severe bug. I may consider not using this model in production due to this."},
                                        {"value": "5: This is so severe that no model with this bug should be in production."},
                                    ],
                                }
                            }
                        },
                    },
                    "location": {
                        "index": id + 1
                    }
                }
            })

    # Creates the initial form
    result = form_service.forms().create(body=NEW_FORM).execute()

    # Adds the question to the form
    question_setting = form_service.forms().batchUpdate(
        formId=result["formId"], body=NEW_QUESTIONS).execute()

    # Prints the result to show the question has been added
    get_result = form_service.forms().get(formId=result["formId"]).execute()
    # print(get_result)
    url = get_result["responderUri"]
    return url


def pair_student_graders(student_info):
    """
    Pairs peer grading. 
    student info is a list with [{idx: student idx, andrewid: student andrewid}]
    Each student will grade three other students, randomly selected.
    Returns a dict with {grader idx: [grading student idx 1, grading student idx 1, grading student idx 1]}
    """
    graders = {}
    # track the number of graders for each student. Should only be graded by up to three people.
    num_graders = {s["idx"]: 0 for s in student_info}
    idxes = [s["idx"] for s in student_info]
    for student in student_info:
        idx = student["idx"]
        graders[idx] = []
        while len(graders[idx]) < 3:
            # randomly select a student to grade
            grader_idx = np.random.choice(idxes)
            if grader_idx not in graders[idx] and num_graders[grader_idx] < 3 and grader_idx != idx:
                graders[idx].append(grader_idx)
                num_graders[grader_idx] += 1
    return graders


def generate_text_sent_to_students(student_info, grader_pairs):
    text = ""
    student_info_key = {s["idx"]: s for s in student_info}
    for idx, gradee_idxes in grader_pairs.items():
        local_text = f"------------------ {idx}: {student_info_key[idx]['andrewid']} ----------------------\n"
        first_name = student_info_key[idx]["name"].split(",")[-1].strip()
        local_text += f"Hi {first_name}! You have been assigned to grade the following assignments (forms only accessible if you log into your Andrew account):\n"
        for gradee_idx in gradee_idxes:
            local_text += f"- {student_info_key[gradee_idx]['url']}\n"
        local_text += f"Please follow the instructions in the form to grade the assignment."
        text += local_text + "\n\n"
    # write the text to a file
    with open("email_text.txt", "w") as f:
        f.write(text)


if __name__ == "__main__":
    # unzip_submissions(student_info)
    student_info = load_student_info("student_info.csv")
    #create_gforms(student_info, "A1-grading")

    #
    # print(graders)
    #create_one_gform(1, "malbayra", "A1-grading-test")
    # get_result = form_service.forms().get(
    #    formId="1Vi7o8jtGs1sbBv7qf9B_MjrRCLqqprumDs1fkzl_NlQ").execute()
    # print(get_result)
    graders = pair_student_graders(student_info)
    generate_text_sent_to_students(student_info, graders)
