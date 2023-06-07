from __future__ import print_function

import os.path
import logging
import base64
import email
import html


from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pprint import pprint
from ast import literal_eval
from datetime import datetime, timedelta

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
SENDER_EMAIL = "anirudh.skumar.03@gmail.com"
REQD_LABEL = "Test"
DONE_LABEL = "Test/Complete"
REQD_TEXT = "has been approved by Dofa"
TIME_DELTA_HOUR: int = 2
TIME_DELTA_DAY:int = 0

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GetMail")

after_time = timedelta(hours=TIME_DELTA_HOUR, days=TIME_DELTA_DAY)
after_time_str = (datetime.now() - after_time).strftime("%Y/%m/%d")
gmail = None

def quote_text(text):
    """For a given string, return the text inside single quotes.
    For example, for the string "Hello 'World'", return "World".
    """

    for i in range(len(text)):
        if text[i] == "'":
            for j in range(i+1, len(text)):
                if text[j] == "'":
                    return text[i+1:j]
            return None


def init():
    """Initializez the client library."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        gmail = build('gmail', 'v1', credentials=creds)
    except HttpError as error:
        logger.error(f'An error occurred: {error}')
    
    logger.info("Service created")
    return gmail

def getMessages(service):
    """Returns ID of emails to be processed.
    """
    # Call the Gmail API to only get emails from a specific sender
    results = service.users().messages().list(userId='me', q=f'from:{SENDER_EMAIL}').execute()
    messages = results.get('messages', [])
    rval: list[str] = []
    if messages:
        # Get content of the email
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            skip = True
            for i in msg.get('payload').get('parts'):
                # print(datetime.fromtimestamp(int(msg.get('internalDate'))/1000))
                ## Only looking at every alternate email
                skip = not skip
                if skip:
                    continue
                
                ## get the label of the email, skip if not REQD_LABEL
                label = msg.get('labelIds')
                ## Convert ID to string
                for j in range(len(label)):
                    label[j] = service.users().labels().get(userId='me', id=label[j]).execute().get('name')

                if (REQD_LABEL not in label):
                    continue

                ## Getting the text and filtering it
                text = (base64.urlsafe_b64decode(i.get('body').get('data')))
                text = text.decode('utf-8')

                ## If REDQ_TEXT is not in the text, skip
                if (REQD_TEXT not in text):
                    continue

                rval.append(message['id'])
                logger.info(f"Message with ID {message['id']} added to list")

        return rval
    else:
        logger.info('No messages found.')

def getEventDetails(service, msg_list):
    """Takes message IDs, processes the text and returns a list of events.
    """
    rval: list[dict] = []

    messages: list[str] = []
    # Get the text from the email
    for i in msg_list:
        message = service.users().messages().get(userId='me', id=i).execute()
        for j, i in enumerate(message.get('payload').get('parts')):
            if (not j%2):
                text = (base64.urlsafe_b64decode(i.get('body').get('data'))).decode('utf-8')
                text = text.replace('\r', '')
                messages.append(text)
    
    # Process the text
    messages = [i.split('\n') for i in messages]
    messages = [[j for j in i if j] for i in messages]

    # Get the event details
    for i in messages:
        event: dict = {}
        event['name'] = quote_text(i[2]) 
        event['category'] = quote_text(i[3])
        event['start'] = quote_text(i[4])
        event['end'] = quote_text(i[5])
        rval.append(event)

    print(messages)


def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """

    try:
        # Call the Gmail API
        gmail = init()
        m_ids: list[str] = getMessages(gmail)
        if (m_ids):
            getEventDetails(gmail, m_ids)

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')


if __name__ == '__main__':
    main()