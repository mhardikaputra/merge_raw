import os
import json
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# 1. Load credentials securely from the GitHub Secret environment variable
creds_json = os.environ.get('GCP_CREDENTIALS')
creds_dict = json.loads(creds_json)

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Use from_service_account_info instead of from_service_account_file
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)

# 2. Connect to the sheets
sheet1 = client.open_by_url("https://docs.google.com/spreadsheets/d/1a6gdPuWWeIqcdw5YnUQBHppHt_OkZ2yNw_Fi5iPhSvg/edit?gid=0#gid=0").worksheet("Raw Data")
sheet2 = client.open_by_url("https://docs.google.com/spreadsheets/d/1s8Xzfr3OdD1Ty3HScdVUB9bNHQxXtwGf0N7HnztNFfM/edit?gid=1179090678#gid=1179090678").worksheet("RAW DATA")
dest_sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1VfbKcNo8In9poUbsKKnZ-xjD3WZ3u0iXV6fKiR8OU6o/edit?gid=0#gid=0").worksheet("Merged Raw")

# 3. Pull and merge data
df1 = pd.DataFrame(sheet1.get_all_records())
df2 = pd.DataFrame(sheet2.get_all_records())
merged_df = pd.concat([df1, df2], ignore_index=True)

# 4. Upload to destination
upload_data = [merged_df.columns.values.tolist()] + merged_df.values.tolist()
dest_sheet.clear()
dest_sheet.update(range_name='A1', values=upload_data)
