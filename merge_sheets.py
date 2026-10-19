import os
import json
import time
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

# 3. Pull data
print("Downloading data...")
data1 = sheet1.get_all_values()
data2 = sheet2.get_all_values()

df1 = pd.DataFrame(data1[1:], columns=data1[0])
df2 = pd.DataFrame(data2[1:], columns=data2[0])
merged_df = pd.concat([df1, df2], ignore_index=True)

# 4. Resize the destination sheet to fit the incoming data
total_rows_needed = len(merged_df) + 1  # +1 for the header row
print(f"Resizing destination sheet to {total_rows_needed} rows...")

# Get current row count and add rows if needed
current_rows = dest_sheet.row_count
if total_rows_needed > current_rows:
    dest_sheet.add_rows(total_rows_needed - current_rows)

# 5. Upload to destination in chunks to prevent Google API timeouts
print(f"Preparing to upload {len(merged_df)} rows...")
upload_data = [merged_df.columns.values.tolist()] + merged_df.values.tolist()
dest_sheet.clear()

chunk_size = 10000  # Upload 10,000 rows at a time
for i in range(0, len(upload_data), chunk_size):
    chunk = upload_data[i:i + chunk_size]
    start_row = i + 1
    
    # Upload the chunk starting at the correct row
    dest_sheet.update(range_name=f'A{start_row}', values=chunk)
    
    print(f"Uploaded rows {start_row} to {start_row + len(chunk) - 1}")
    time.sleep(2)  # Pause for 2 seconds to avoid rate limiting

print("Success! Sheets merged and uploaded.")
