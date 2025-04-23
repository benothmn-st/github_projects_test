from github import Github
from datetime import datetime, timedelta
import os
import sys

# Initialize GitHub client
ACCESS_TOKEN = os.getenv('GH_TOKEN')
REPO_NAME = "benothmn-st/github_projects_test"
PROJECT_NUMBER = 1  # Your project number

if not ACCESS_TOKEN:
    print("Error: GH_TOKEN environment variable not set.", file=sys.stderr)
    sys.exit(1)

g = Github(ACCESS_TOKEN)

# Fetch the repository
try:
    repo = g.get_repo(REPO_NAME)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
#repo_names = [repo.name for repo in g.get_repos()]

#with open('GITHUB_OUTPUT', 'w') as file:
    #file.write(', '.join(repo_names))
#exit()

# Find the project
project = None
for proj in repo.get_projects():
    if proj.number == PROJECT_NUMBER:
        project = proj
        break

if not project:
    raise Exception("Project not found")

# Calculate date range
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

# Get all project columns (statuses)
columns = project.get_columns()

# Initialize metrics
metrics = {
    'opened_issues': [],
    'closed_issues': [],
    'status_counts': {},
    'cycle_times': []
}

# Get all issues in the project
for column in columns:
    column_name = column.name
    metrics['status_counts'][column_name] = []
    
    for card in column.get_cards():
        issue = card.get_content()
        
        if not issue or not hasattr(issue, 'title'):  # Skip notes
            continue
            
        # Issues in this status
        metrics['status_counts'][column_name].append(issue.title)
        
        # Check if closed in last week
        if issue.closed_at and start_date <= issue.closed_at <= end_date:
            metrics['closed_issues'].append({
                'title': issue.title,
                'closed_at': issue.closed_at,
                'created_at': issue.created_at,
                'cycle_time': (issue.closed_at - issue.created_at).days
            })
        
        # Check if created in last week
        if start_date <= issue.created_at <= end_date:
            metrics['opened_issues'].append(issue.title)

# Calculate additional metrics
metrics['total_open'] = sum(len(issues) for status, issues in metrics['status_counts'].items() if status.lower() != 'done')
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

## Work Status Breakdown
"""

for status, issues in metrics['status_counts'].items():
    report += f"- {status}: {len(issues)} issues\n"

report += "\n## Recently Closed Issues\n"
for issue in metrics['closed_issues']:
    report += f"- {issue['title']} (Cycle time: {issue['cycle_time']} days)\n"

report += "\n## Performance Metrics\n"
report += f"- Average cycle time: {metrics['avg_cycle_time']:.1f} days\n"

print(report)
