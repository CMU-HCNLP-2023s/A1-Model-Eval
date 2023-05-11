from __future__ import print_function
import json
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


def get_one_response(andrewid, form_url):
    """
    Gets the response for one student.
    index is the student's index in the student_info dict
    andrewid is the student's andrewid
    Returns the response.
    """
    SCOPES = "https://www.googleapis.com/auth/forms.responses.readonly"
    DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"

    store = file.Storage('token.json')
    creds = None
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_secrets.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = discovery.build('forms', 'v1', http=creds.authorize(
        Http()), discoveryServiceUrl=DISCOVERY_DOC, static_discovery=False)

    # Prints the responses of your specified form:
    form_id = form_url.replace("https://drive.google.com/open?id=", "").replace(
        "&usp=drive_copy", "").replace("https://docs.google.com/forms/d/", "").replace("/edit", "")
    print(form_id)
    # get_result = service.forms().get(formId=form_id).execute()
    # print(get_result)
    result = service.forms().responses().list(formId=form_id).execute()
    print(result)


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

    # Request body for creating a form
    with open("grade_instruction.txt", "r") as f:
        general_instruction = f.read()

    nocode_ids = ["ryanliu"]
    is_not_code = andrewid in nocode_ids

    options_code = [
        {"value": "1: The model does not fail on this test enough for me to consider it a bug."},
        {"value": "2: It fails enough that I think this is a minor bug."},
        {"value": "3: This is a bug that is worth investigating and fixing."},
        {"value": "4: This is a severe bug. I may consider not using this model in production due to this."},
        {"value": "5: This is so severe that no model with this bug should be in production."},
    ]
    options_nocode = [
        {"value": "1: The test is focusing on a minor aspect, and I wouldn't worry too much about a model failing on it."},
        {"value": "2: If a model has a high enough error rate on this (e.g., fails for 50/100), then I think this reflects a minor bug."},
        {"value": "3: If a model has a high enough error rate on this (e.g., fails for 50/100), then this is a bug that is worth investigating and fixing."},
        {"value": "4: If a model has a high enough error rate on this (e.g., fails for at least 50/100), then I would say this is a severe bug. I may consider not using this model in production due to this."},
        {"value": "5: If a model has a high enough error rate on this (e.g., fails for at least 50/100), then this is so severe that no model with this bug should be in production."},
    ]

    def clean_markdown_format(text):
        """
        Cleans up the markdown format for the question.
        """
        # text = text.replace("###", "")
        text = text.replace("*", "")
        text = re.sub(r"\n\n+", "\n\n", text)
        # text = re.sub(r"^\\t+-", "-", text)
        # text = re.sub(r"^\s+-", "-", text)
        # text = re.sub(r"^-", "    -", text)
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

    NEW_FORM = {
        "info": {
            "title": f"{title} - #{idx}{' (No Code)' if is_not_code else ''}",
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
    included_tests = {
        "ryanliu": [4, 5, 8],
        "pvaidos": [7, 8, 9],
    }
    # add the tests
    item_idxes = 1
    id = 0
    for test_idx, test in enumerate(tests):
        if andrewid in included_tests and (test_idx + 1) not in included_tests[andrewid]:
            continue
        id += 1
        test = clean_markdown_format(test)
        if test:
            splits = test.split('\n')
            title, content = splits[0], '\n'.join(splits[1:])
            title = f"Test {id}: {title}"
            NEW_QUESTIONS["requests"].append({
                "createItem": {
                    "item": {
                        "title": f"{title}",
                        "description": f"----\n\n {content} \n\n---\n",
                        "textItem": {}
                    },
                    "location": {
                        "index": item_idxes
                    }
                }
            })
            NEW_QUESTIONS["requests"].append({
                "createItem": {
                    "item": {
                        "title": f"Rating: [{title}]. Would you consider a bug exposed by this test to be severe?",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "choiceQuestion": {
                                    "type": "RADIO",
                                    "options": options_code if not is_not_code else options_nocode,
                                }
                            }
                        },
                    },
                    "location": {
                        "index": item_idxes+1
                    }
                },

            })
            NEW_QUESTIONS["requests"].append({

                "createItem": {
                    "item": {
                        "title": f"Describe: [{title}]. Write a justification for your rating.",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "textQuestion": {
                                    "paragraph": True
                                }
                            }
                        },
                    },
                    "location": {
                        "index": item_idxes+2
                    }
                }
            })
            item_idxes += 3
    NEW_QUESTIONS["requests"].append({
        "createItem": {
            "item": {
                "title": f"Overall feedback: Do you have any more suggestions and/or thoughts on the task/model/tests?",
                "questionItem": {
                    "question": {
                        "required": False,
                        "textQuestion": {
                            "paragraph": True
                        }
                    }
                },
            },
            "location": {
                "index": item_idxes
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
    print(grader_pairs)
    with open("email_text.txt", "w") as f:
        f.write(text)
    # write the grader info to a separate json file
    # with open("grader_info.json", "w") as f:
    #    json.dump(dict(grader_pairs), f, indent=4)


def generate_grading_report():  # Load CSV file into a Pandas dataframe
    text = ""
    df = pd.read_csv('student_grades.csv')
    quartiles = [(round(n, 3), 5*(i+1)) for i, n in enumerate(np.percentile(
        df['Peer Rating'][df['Peer Rating'].notna()], [0, 25, 50, 75, 100]))]
    print(quartiles)
    quantile_info = f"\t Top 25%: >={quartiles[3][0]}; Top 50%: >={quartiles[2][0]}; Top 75%: >={quartiles[1][0]}"
    columns = [c for c in df.columns if c not in [
        "Student", "index", "andrewid"]]
    # Loop through each row in the dataframe
    for _, row in df.iterrows():
        # Create a list to hold the row data
        local_text = f"------------------ {row['index']}: {row['andrewid']} ----------------------\n"
        first_name = row["Student"].split(",")[-1].strip()
        local_text += f"Hi {first_name}! Here's your grade details:\n"
        # Loop through each column in the row
        for column in columns:
            if column == "Peer Rating":
                peer_grade = row[column]
                for j, q in enumerate(quartiles):
                    try:
                        if peer_grade < q[0] or (j == 4 and peer_grade == q[0]):
                            i = j-1
                            if i != 0:
                                explain_rank = f", in Top {(4-i)*25}% of the class"
                            else:
                                explain_rank = ""
                            local_text += f'Peer Rating: {np.round(peer_grade, 2)}{explain_rank}\n'
                            local_text += f'{quantile_info}\n'
                            row["Peer Score"] = quartiles[i][1]
                            row["Total Score"] = row["Peer Score"] + \
                                row["Base Score"]
                            break
                    except Exception as e:
                        print(e)
            else:
                # Get the cell value for the current row and column
                cell_value = row[column]
                column = f"**{column}**" if "Score" in column else column
                # Append the cell value to the row list
                local_text += f'{column}: {cell_value}\n'
        text += local_text + "\n\n"
        with open("grade_text.txt", "w") as f:
            f.write(text)
        # Print the row list


def generate_milestone_report():  # Load CSV file into a Pandas dataframe
    text = ""
    df = pd.read_csv('final_present.csv')
    columns = [c for c in df.columns if c not in [
        "Project title", "Order"]]
    # Loop through each row in the dataframe
    for _, row in df.iterrows():
        # Create a list to hold the row data
        local_text = f"Comment to project: {row['Project title']}\n----------------------------------------\n"
        # Loop through each column in the row
        scores = 0
        for column in columns:
            # Get the cell value for the current row and column
            cell_value = row[column]
            # Append the cell value to the row list

            if column not in ["Note", "Groupmates"]:
                local_text += f'{column}: {cell_value} / 5\n'
                scores += cell_value
            else:
                local_text += f'{column}: {cell_value}\n'
        local_text += f"Total score: {scores} / {15} * 45 = {45/15*scores}\n"
        text += local_text + "\n\n"
        with open("final_text.txt", "w") as f:
            f.write(text)
        # Print the row list


if __name__ == "__main__":
    # unzip_submissions(student_info)
    # student_info = load_student_info("student_info.csv")
    # create_gforms(student_info, "A1-grading")

    #
    # print(graders)
    # create_one_gform(1, "malbayra", "A1-grading-test")
    # get_result = form_service.forms().get(
    #    formId="1Vi7o8jtGs1sbBv7qf9B_MjrRCLqqprumDs1fkzl_NlQ").execute()
    # print(get_result)
    # graders = pair_student_graders(student_info)
    # generate_text_sent_to_students(student_info, graders)
    # get_one_response(
    #    "malbayra",
    #    "https://drive.google.com/open?id=1vq3GwMIMncjZUXOEYI3fUm5qO08A8twC1SzC3wuvXEI&usp=drive_copy")
    generate_milestone_report()
