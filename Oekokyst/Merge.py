# -*- coding: utf-8 -*-
"""
Created on Mon Feb 16 21:56:25 2026

@author: rutvin
"""

import pandas as pd
import os
import glob

#Merging several files with different tabnames to one file

# =============================================================================
# # 1. Define the input directory and output file path
# input_dir = r'C:\GIT\Oekokyst\Vannmiljødata\Split' # Replace with your directory path
# output_file = r'C:\GIT\Oekokyst\Data\merge.xlsx'
# 
# # 2. Get a list of all Excel files in the directory
# excel_files = glob.glob(os.path.join(input_dir, '*.xlsx'))
# 
# if not excel_files:
#     print("No Excel files found in the specified directory.")
# else:
#     # 3. Create an ExcelWriter object for the output file
#     with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
#         # 4. Loop through each Excel file
#         for file_path in excel_files:
#             file_name = os.path.basename(file_path)
#             print(f"Processing file: {file_name}")
# 
#             # Read all sheets from the current file into a dictionary of DataFrames
#             # sheet_name=None returns a dictionary where keys are sheet names and values are DataFrames
#             all_sheets_dict = pd.read_excel(file_path, sheet_name=None)
# 
#             # 5. Loop through each sheet in the dictionary
#             for sheet_name, df in all_sheets_dict.items():
#                 # Create a unique sheet name in the output file
#                 # You can customize this naming convention
#                 unique_sheet_name = sheet_name
#                 
#                 # 6. Write the DataFrame to a specific sheet in the output file
#                 df.to_excel(writer, sheet_name=unique_sheet_name, index=False)
#                 print(f"  - Appended sheet: {unique_sheet_name}")
# 
#     print(f"\nAll sheets combined successfully into '{output_file}'.")
# =============================================================================

#Merging new data (one new file per month with master file)

import pandas as pd

def combine_excel_sheets_by_name(file1_path, file2_path, output_path):
    """
    Combines two Excel files, concatenating sheets with the same name 
    into a single sheet in a new output file.
    """
    
    # 1. Read all sheets from both Excel files into dictionaries of DataFrames
    # sheet_name=None returns a dictionary where keys are sheet names and 
    # values are DataFrames.
    sheets1 = pd.read_excel(file1_path, sheet_name=None)
    sheets2 = pd.read_excel(file2_path, sheet_name=None)

    # Initialize an Excel writer for the output file
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        # 2. Iterate through the sheet names in the first file
        for sheet_name, df1 in sheets1.items():
            # 3. Check if the same sheet name exists in the second file
            if sheet_name in sheets2:
                df2 = sheets2[sheet_name]
                # 4. Concatenate the DataFrames with the same name
                combined_df = pd.concat([df1, df2], ignore_index=True, sort=False)
                
                # 5. Write the combined DataFrame to the new Excel file under the original sheet name
                combined_df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                # If the sheet only exists in file1, write it as is
                df1.to_excel(writer, sheet_name=sheet_name, index=False)

        # 6. Iterate through sheets in the second file that were not in the first
        for sheet_name, df2 in sheets2.items():
            if sheet_name not in sheets1:
                # Write the unique sheet from file2 to the new Excel file
                df2.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"Successfully combined data into {output_path}")

# Example Usage:
file1 = r'C:\GIT\Oekokyst\Data\merge.xlsx'
file2 = r'C:\GIT\Oekokyst\Data\VT8_split.xlsx'
output_file = r'C:\GIT\Oekokyst\Data\merge-new.xlsx'

# Ensure you have 'file1.xlsx' and 'file2.xlsx' in your directory 
# with some sample data and sheets.
combine_excel_sheets_by_name(file1, file2, output_file)