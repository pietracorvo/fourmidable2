import requests
import json


def send_slack(message):
    """Sends a slack messagae to Luka's profile"""
    wekbook_url = 'https://hooks.slack.com/services/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'
    data = {'text': message}
    response = requests.post(wekbook_url, data=json.dumps(
        data), headers={'Content-Type': 'application/json'})
