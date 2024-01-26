import sys
import json
import requests
import pytz
from datetime import datetime, timedelta

from issue import Issue

DISCUSSION_REPO_OWNER = sys.argv[1]  # Discussion Repository Owner's Username
DISCUSSION_REPOSITORY = sys.argv[2]  # Discussion Repository Name
ISSUE_REPO_OWNER = sys.argv[3]  # Issue Repository Owner's Username
ISSUE_REPOSITORY = sys.argv[4]  # Issue Repository Name
DISCUSSION_NO = sys.argv[5] # Discussion Number
GITHUB_PERSONAL_ACCESS_TOKEN = sys.argv[6] # Personal Access Token
WEEK_OFFSET = int(sys.argv[7]) # OFFSET WEEK (Integer)

# Define a custom sorting key function
def custom_sort_key(issue):
    # Define the order of project statuses
    status_order = {
        "Open": 1,
        "Reopened": 2,
        "In Progress": 3,
        "Need Review": 4,
        "Review In Progress": 5,
        "Done": 6,
        "Paused": 7,
        "Recurring": 8,
    }
    # print(issue)
    # Assign a default value for sorting if complete_date or deadline is None
    default_complete_date = issue.complete_date or "9999-99-99"
    default_deadline = issue.deadline or "9999-99-99"

    # Return a tuple for sorting, with project_status being the key
    return (
        status_order.get(issue.project_status, 9),
        default_complete_date,
        default_deadline,
    )


# Query for Fetching discussion node id
query = """
query {
  repository(owner: "%REPO-OWNER%", name: "%REPOSITORY%") {
    discussion(number: %DISCUSSION_NO%) {
      id
    }
  }
}
"""

query = (
    query.replace("%REPO-OWNER%", DISCUSSION_REPO_OWNER)
    .replace("%REPOSITORY%", DISCUSSION_REPOSITORY)
    .replace("%DISCUSSION_NO%", str(DISCUSSION_NO))
)

# Define your GitHub API endpoint
endpoint = "https://api.github.com/graphql"  # Replace with your GraphQL endpoint

# Define your GitHub Personal Access Token
token = GITHUB_PERSONAL_ACCESS_TOKEN

# Set up the headers with your token
headers = {
    "Authorization": f"Bearer {token}",
}

# Make the GraphQL request
response = requests.post(endpoint, json={"query": query}, headers=headers)

print(response.json())

discussion_id = response.json()["data"]["repository"]["discussion"]["id"]

print(discussion_id)

# Fetch Issues
query = """
{
  repository(owner: "%REPO-OWNER%", name: "%REPOSITORY%") {
    issues(last: 100, orderBy: {field: CREATED_AT, direction: DESC}) {
      edges {
        node {
          number
          title
          url
          closed
          createdAt
          closedAt
          projectItems(first: 1) {
            totalCount
            edges {
              node {
                project {
                  title
                }
                updatedAt
                id
                fieldValues(first: 20) {
                  nodes {
                    ... on ProjectV2ItemFieldSingleSelectValue {
                      field {
                        ... on ProjectV2SingleSelectField {
                          name
                        }
                      }
                      name
                    }
                    ... on ProjectV2ItemFieldDateValue {
                      field {
                        ... on ProjectV2Field {
                          name
                        }
                      }
                      date
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""
query = query.replace("%REPO-OWNER%", ISSUE_REPO_OWNER).replace("%REPOSITORY%", ISSUE_REPOSITORY)

# Make the GraphQL request
response = requests.post(endpoint, json={"query": query}, headers=headers)

# Check the response
if response.status_code == 200:
    data = response.json()
    # print(data)

    # Extract issue items
    issues = data["data"]["repository"]["issues"]["edges"]

    # Define a list to store the extracted issues as instances of the Issue class
    issue_list = []
    # Iterate through the issues and extract the required fields
    for issue in issues:
        node = issue["node"]
        issue_title = node["title"]
        issue_url = node["url"]
        is_closed = node["closed"]
        created_at = node["createdAt"]
        closed_at = node["closedAt"]
        number = node["number"]

        deadline = None
        start_date = None
        complete_date = None
        project_status = None

        project_items = node["projectItems"]["edges"]
        if project_items:
            if project_items[0]["node"]["project"]:
                project = project_items[0]["node"]["project"]
            if project["title"]:
                project_title = project["title"]
            nodes = project_items[0]["node"]["fieldValues"]["nodes"]
            for node_item in nodes:
                # print(node_item)
                if node_item:
                    if node_item["field"]["name"] == "Deadline":
                        deadline = node_item["date"]
                    if node_item["field"]["name"] == "Started":
                        start_date = node_item["date"]
                    if node_item["field"]["name"] == "Completed":
                        complete_date = node_item["date"]
                    if node_item["field"]["name"] == "Status":
                        project_status = node_item["name"]
            # if project_items[0]["node"]["fieldValues"]["nodes"][1]["name"]:
            #     project_status = project_items[0]["node"]["fieldValues"]["nodes"][1]["name"]
            # if project_items[0]["node"]["fieldValues"]["nodes"][2]["date"]:
            #     start_date = project_items[0]["node"]["fieldValues"]["nodes"][2]["date"]
            # if project_items[0]["node"]["fieldValues"]["nodes"][4]["date"]:
            #     complete_date = project_items[0]["node"]["fieldValues"]["nodes"][4]["date"]
            # if project_items[0]["node"]["fieldValues"]["nodes"][5]["date"]:
            #     deadline = project_items[0]["node"]["fieldValues"]["nodes"][5]["date"]
        else:
            project_title = (
                project_status
            ) = start_date = complete_date = deadline = None

        issue = Issue(
            number,
            issue_title,
            issue_url,
            is_closed,
            created_at,
            closed_at,
            project_title,
            project_status,
            start_date,
            complete_date,
            deadline,
        )
        issue_list.append(issue)

    # Print the extracted issue items using the Issue class
    # for issue in issue_list:
    #     print(issue)

    # print(len(issue_list))

    # Create date list of last 7 days

    # Define the date format
    date_format = "%Y-%m-%d"

    # Get the current date
    current_date = datetime.now(pytz.timezone("Asia/Dhaka"))

    # Create a list to store the dates
    date_list = []

    # Generate the list of 8 dates
    for _ in range(8):
        date_list.append(current_date.strftime(date_format))
        current_date -= timedelta(days=1)

    # Reverse the list to have the dates in descending order
    date_list.reverse()

    # Print the list of dates
    # for date in date_list:
    #     print(date)

    ## Filtering Issues
    filtered_issue_list = [
        issue
        for issue in issue_list
        if (issue.complete_date in date_list)
        or (
            issue.project_status
            in [
                "In Progress",
                "Open",
                "Reopened",
                "Review In Progress",
                "Need Review",
                "Paused",
                "Recurring",
            ]
        )
    ]

    # Sort the filtered list using the custom sorting key
    sorted_issue_list = sorted(filtered_issue_list, key=custom_sort_key)

    # Separate different issue status
    completed_issue_list = [
        issue for issue in sorted_issue_list if (issue.project_status in [
                "Done",
                "Review In Progress",
                "Need Review",
            ])
    ]
    ongoing_issue_list = [
        issue for issue in sorted_issue_list if (issue.project_status in [
                "In Progress",
                "Reopened",
            ])
    ]

    future_issue_list = [
        issue for issue in sorted_issue_list if (issue.project_status in [
                "Open",
            ])
    ]

    week_start = (datetime.now(pytz.timezone("Asia/Dhaka")) - timedelta(days=7)).strftime("%b %d, %Y")
    week_end = (datetime.now(pytz.timezone("Asia/Dhaka")) - timedelta(days=1)).strftime("%b %d, %Y")
    
    # Generate Comment Body
    body = "## Week " + str(
        datetime.now().isocalendar()[1] - WEEK_OFFSET
    )  # get week number
    body += "\n\n#### Date: {} to {} ".format(week_start,week_end)

    # completed tasks
    body += "\n\n### Completed Task"
    for issue in completed_issue_list:
        body += "\n- [" + issue.title + " #" + str(issue.number) + "](" + issue.url + ")"
    
    # Ongoing tasks
    body += "\n\n### Ongoing Task"
    for issue in ongoing_issue_list:
        body += "\n- [" + issue.title + " #" + str(issue.number) + "](" + issue.url + ")"
    
    # Next tasks
    body += "\n\n### Plan for Next Week"
    for issue in future_issue_list:
        body += "\n- [" + issue.title + " #" + str(issue.number) + "](" + issue.url + ")"
    
    # Dependencies
    body += "\n\n### Dependencies"
    body += "\n- "

    print(body)
    
    # Create Comment on Discussion Thread
    query = """
    mutation {
    addDiscussionComment(input: {discussionId: "%discussionId%", body: "%BODY%"}) {
        # response type: Comment
        comment {
        id
        }
    }
    }
    """

    query = query.replace("%discussionId%", discussion_id).replace("%BODY%",body)

    # Make the GraphQL request
    response = requests.post(endpoint, json={'query': query}, headers=headers)

    print(response.json())

else:
    print(f"Request failed with status code: {response.status_code}")
    print(response.text)


