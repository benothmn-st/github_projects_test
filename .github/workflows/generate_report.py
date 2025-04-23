import os
import sys
import requests
from datetime import datetime, timedelta

# Initialize GitHub client
ACCESS_TOKEN = os.getenv('GH_TOKEN')
REPO_OWNER = "benothmn-st"
REPO_NAME = "github_projects_test"
PROJECT_NUMBER = 1  # Your project number

if not ACCESS_TOKEN:
    print("Error: GH_TOKEN environment variable not set.", file=sys.stderr)
    sys.exit(1)

# Calculate date range
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

# GraphQL query to fetch project details
query = f"""
{{
  repository(owner: "{REPO_OWNER}", name: "{REPO_NAME}") {{
    projectsV2(first: 10) {{
      nodes {{
        number
        title
        items(first: 100) {{
          nodes {{
            content {{
              ... on Issue {{
                title
                createdAt
                closedAt
              }}
            }}
          }}
        }}
      }}
    }}
  }}
}}
"""

headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
response = requests.post('https://api.github.com/graphql', json={'query': query}, headers=headers)

if response.status_code != 200:
    raise Exception(f"Query failed to run by returning code of {response.status_code}. {response.text}")

# Parse the response
data = response.json()
projects = data['data']['repository']['projectsV2']['nodes']

# Find the project
project = next((proj for proj in projects if proj['number'] == PROJECT_NUMBER), None)

if not project:
    raise Exception("Project not found")

# Initialize metrics
metrics = {
    'opened_issues': [],
    'closed_issues': [],
    'status_counts': {},
    'cycle_times': []
}

# Process project items
for item in project['items']['nodes']:
    content = item['content']
    if content:
        title = content['title']
        created_at = datetime.fromisoformat(content['createdAt'].replace('Z', '+00:00')).replace(tzinfo=None)
        closed_at = content.get('closedAt')
        closed_at = datetime.fromisoformat(closed_at.replace('Z', '+00:00')).replace(tzinfo=None) if closed_at else None

        # Check if closed in last week
        if closed_at and start_date <= closed_at <= end_date:
            metrics['closed_issues'].append({
                'title': title,
                'closed_at': closed_at,
                'created_at': created_at,
                'cycle_time': (closed_at - created_at).days
            })

        # Check if created in last week
        if start_date <= created_at <= end_date:
            metrics['opened_issues'].append(title)

# Calculate additional metrics
metrics['total_open'] = len(metrics['opened_issues'])  # Assuming all opened issues are still open
metrics['net_change'] = len(metrics['opened_issues']) - len(metrics['closed_issues'])
metrics['avg_cycle_time'] = sum(issue['cycle_time'] for issue in metrics['closed_issues']) / len(metrics['closed_issues']) if metrics['closed_issues'] else 0

# Generate report
report = f"""
# Weekly GitHub Project Report ({start_date.date()} to {end_date.date()})

## Issue Evolution
- New issues opened: {len(metrics['opened_issues'])}
- Issues closed: {len(metrics['closed_issues'])}
- Net change in open issues: {metrics['net_change']}
- Total open issues: {metrics['total_open']}

## Recently Closed Issues
"""

for issue in metrics['closed_issues']:
    report += f"- {issue['title']} (Cycle time: {issue['cycle_time']} days)\n"

report += "\n## Performance Metrics\n"
report += f"- Average cycle time: {metrics['avg_cycle_time']:.1f} days\n"

print(report)
