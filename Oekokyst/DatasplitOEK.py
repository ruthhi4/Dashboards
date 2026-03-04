# -*- coding: utf-8 -*-
"""
Created on Mon Feb 16 18:44:49 2026

@author: rutvin
"""

import pandas as pd
import glob as glob

#Folder_For_Data = r'C:\GIT\Oekokyst\Vannmiljødata\Test\*.xlsx'

Folder_For_Data = r'C:\Users\rutvin\OneDrive - Norconsult Group\Documents\Python Scripts\Øyeren\Data\*.xlsx'

df_obs = []

for file in glob.glob(Folder_For_Data):
    dfx = pd.read_excel(file, keep_default_na=False)
    # print(file)                 
    df_obs.append(dfx)
df_obs = pd.concat(df_obs, sort=False, ignore_index=True)   

#a = ['TEMP', 'SALIN', 'TURB', 'O2', 'P-TOT', 'P-PO4', 'N-TOT', 'N-SNOX', 'N-NH4', 'SI-SO2', 'SECCI', 'KLFA', 'TSM', 'DOC', 'CDOM', 'POC', 'PON', 'POP'] #KD_PAR
a = ['E-KOLI', 'N-NO2', 'N-NO3', 'N-TOT', 'P-ORTO', 'P-TOT', 'S-GR', 'STS', 'TOC']

#df_obs2 = df_obs[df_obs.Parameter_id.isin(a)]
df_obs3 = df_obs[df_obs.Parameter_id.isin(a)]


# df_obs2['Ovre_dyp'] = pd.to_numeric(df_obs2['Ovre_dyp'],errors='coerce')

# b= [0,5,10,20,30]
# df_obs3 = df_obs2[df_obs.Ovre_dyp.isin(b)]


# myDict = {
#     '02.42-57155'  : 'VT8',
#     '02.60-84110'  : 'VT74',
#     '02.42-84204' : 'VT83',
#     '02.80-87369' : 'VT79',
#     '02.42-84205' : 'VR49',
#     '02.60-63422' : 'VT70',
#     '02.60-87372' : 'VT53',
#     '02.80-87368' : 'VT16'
#     }






df_obs3['Parameter_id'] = df_obs3['Parameter_id'].str.strip()
df_obs3['Vannlokalitet_kode'] = df_obs3['Vannlokalitet_kode'].str.strip()
# df_obs3['Vannlokalitet_kode'] = df_obs3['Vannlokalitet_kode'].map(myDict)

# df_obs3['Vannlokalitet_kode'] = df_obs3['Vannlokalitet_kode'] + '_' + df_obs3['Ovre_dyp'].astype(str) + 'm'


# # #print(df_obs3)
# # print(df_obs3.dtypes)

df_obs3.loc[df_obs3['Operator'] == '<','value'] = df_obs3['Operator'].astype(str)  + df_obs3['Verdi'].astype(str) 
df_obs3.loc[df_obs3['Operator'] == '>','value'] = df_obs3['Operator'].astype(str)  + df_obs3['Verdi'].astype(str) 
df_obs3.loc[df_obs3['Operator'] == '=','value'] = df_obs3['Verdi'].astype(str) 

# print(df_obs3)

#Duplicate test, error message if no duplicates
df_obs3['duplicate'] =   df_obs3['Tid_provetak'] + df_obs3['Parameter_id'] + df_obs3['Vannlokalitet_kode'] + df_obs3['Ovre_dyp'].astype(str)
dup_list = pd.concat(g for _, g in df_obs3.groupby("duplicate") if len(g) > 1)
print(dup_list)

# #dup_list.to_excel("C:\\Users\\RUTVIN\\OneDrive - Norconsult Group\\Documents\\Python Scripts\\Glomma\\duplicates.xlsx") 



# # with pd.ExcelWriter(r'C:\GIT\Oekokyst\Vannmiljødata\Split\Historical_data.xlsx') as writer:
# with pd.ExcelWriter(r'C:\Users\rutvin\OneDrive - Norconsult Group\Documents\Python Scripts\Øyeren\Data\Split.xlsx') as writer:
#     for vann_lok_kode, df_tmp in df_obs3.groupby('Vannlokalitet_kode'):
#         df_tmp = df_tmp.pivot(index='Tid_provetak',columns='Parameter_id',values='value')
#         df_tmp.to_excel(writer,sheet_name=vann_lok_kode)

# with pd.ExcelWriter(r'C:\Users\rutvin\OneDrive - Norconsult Group\Documents\Python Scripts\Øyeren\Data\Split.xlsx') as writer: 
#     tmp = df_obs3

#     tmp.to_excel(writer)
