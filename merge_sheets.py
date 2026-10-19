import os
import json
import time
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# --- CONFIGURATION ---
# Type the exact names of the columns that contain the US/ID numbers here.
# (Make sure spelling and capitalization match your headers exactly)
numeric_columns = ['Amount', 'Total', 'Balance'] # <--- UPDATE THIS LIST
# ---------------------

# 1. Load credentials securely from the GitHub Secret environment variable
creds_json = os.environ.get('GCP_CREDENTIALS')
creds_dict = json.loads(creds_json)

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

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

# Create DataFrames
df1 = pd.DataFrame(data1[8808:], columns=data1[0])
df2 = pd.DataFrame(data2[1:], columns=data2[0])

# --- FIX NUMBER FORMATS BEFORE MERGING ---
print("Standardizing number formats...")
for col in numeric_columns:
    if col in df1.columns:
        # Sheet 1 (US format): Remove commas (thousands separator). The dot remains the decimal.
        df1[col] = df1[col].astype(str).str.replace(',', '', regex=False)
        # Convert to pure number (turns text into math)
        df1[col] = pd.to_numeric(df1[col], errors='coerce')
        
    if col in df2.columns:
        # Sheet 2 (ID format): Remove dots (thousands separator), then change comma to dot (decimal)
        df2[col] = df2[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        # Convert to pure number
        df2[col] = pd.to_numeric(df2[col], errors='coerce')
# -----------------------------------------

merged_df = pd.concat([df1, df2], ignore_index=True)

# --- STRICT CLEANUP BASED ON COLUMN B ---
print("Cleaning out blank rows...")
col_b_name = merged_df.columns[1]

merged_df = merged_df[
    (merged_df[col_b_name].astype(str).str.strip() != '') & 
    (merged_df[col_b_name].astype(str).str.lower() != 'nan') &
    (merged_df[col_b_name].astype(str).str.lower() != 'none')
]

merged_df.reset_index(drop=True, inplace=True)
# Fill missing data (including any numbers that failed to convert) with empty strings
merged_df.fillna('', inplace=True)
# ----------------------------------------

# 4. Resize the destination sheet to fit the incoming data
total_rows_needed = len(merged_df) + 1
print(f"Resizing destination sheet to {total_rows_needed} rows...")

current_rows = dest_sheet.row_count
if total_rows_needed > current_rows:
    dest_sheet.add_rows(total_rows_needed - current_rows)

# 5. Upload to destination in chunks to prevent Google API timeouts
print(f"Preparing to upload {len(merged_df)} rows...")
upload_data = [merged_df.columns.values.tolist()] + merged_df.values.tolist()
dest_sheet.clear()

chunk_size = 10000
for i in range(0, len(upload_data), chunk_size):
    chunk = upload_data[i:i + chunk_size]
    start_row = i + 1
    
    dest_sheet.update(range_name=f'A{start_row}', values=chunk)
    print(f"Uploaded rows {start_row} to {start_row + len(chunk) - 1}")
    time.sleep(2)

print("Success! Sheets merged and uploaded.")
