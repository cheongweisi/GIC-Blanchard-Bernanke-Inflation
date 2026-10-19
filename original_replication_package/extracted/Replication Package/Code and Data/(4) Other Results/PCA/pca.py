#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar  2 10:30:36 2023

@author: Sam Boocker and James Lee
"""

import pandas as pd
import os
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

'''
Unless otherwise noted, prices are for first expiring contract for each commodity

'''

# Change directory to where the file is located
try:
    base_dir = os.path.dirname(os.path.realpath("../Replication Package/Code and Data/(4) Other Results/PCA/pca.py"))
    os.chdir(base_dir)
except:
    print("Error: make sure to run entire program at once")

# Import data
'''
Data is for 1st expiring future at the end of each month

Data from Bloomberg

For RBOB gasoline, we only have data back to 2005. So we extrapolate the
trends for unleaded gasoline to recreate data for RBOB going back to at least
1990

For Nickel and Aluminum, we back extrapolate the data as well using the
SP GSCI Spot Index
'''

input_dir = os.path.join(base_dir)

# Import and merge commodity data
bbg_df = pd.read_excel('Bloomberg_Commodity_Data.xlsx', header = 3, sheet_name = "Data_Hard_Copy")

bbg_df = bbg_df.rename(columns = {
    "Unnamed: 0": "Date", "CL1 Comdty": "WTI",
    "HO1 Comdty": "Heating_Oil", "NG1 Comdty": "Natural_Gas",
    "C 1 Comdty": "Corn", "S 1 Comdty": "Soybeans",
    "LC1 Comdty": "Live_Cattle", "GC1 Comdty": "Gold",
    "LA1 Comdty": "Aluminum", "HG1 Comdty": "Copper",
    "SB1 Comdty": "Sugar", "CT1 Comdty": "Cotton",
    "CC1 Comdty": "Cocoa", "KC1 Comdty": "Coffee",
    "LN1 Comdty": "Nickel", "W 1 Comdty": "Wheat",
    "LH1 Comdty": "Lean_Hogs", "JO1 Comdty": "Orange_Juice",
    "SI1": "Silver", "XB1 Comdty": "RBOB_Gasoline",
    "HU1 Comdty": "Unleaded_Gasoline", "TIO1 Comdty": "Iron",
    "LL1 Comdty": "Lead", "LX1 Comdty": "Zinc"})
bbg_df = bbg_df.iloc[2:]
bbg_df["Date"] = pd.to_datetime(bbg_df["Date"])

'''
Extrapolate data for unleaded gasoline backwards
'''
first_rbob_idx = bbg_df["RBOB_Gasoline"].first_valid_index()
for idx in range(first_rbob_idx, bbg_df.index[0], -1):
    new_val = bbg_df.loc[idx, "RBOB_Gasoline"] * (bbg_df.loc[idx-1, "Unleaded_Gasoline"]/bbg_df.loc[idx, "Unleaded_Gasoline"])
    bbg_df.loc[idx-1, "RBOB_Gasoline"] = new_val

bbg_df = bbg_df.drop("Unleaded_Gasoline", axis = 1)

# Use S&P Goldman Sachs Index to extrapolate aluminum and copper further
os.chdir(input_dir)
gsci_df = pd.read_excel("SP_GSCI.xlsx")
gsci_df = gsci_df.rename(columns = {
    "Unnamed: 2": "Date", "Unnamed: 3": "GSCI_Aluminum",
    "Unnamed: 4": "GSCI_Nickel"})
gsci_df = gsci_df.loc[4:, ["Date", "GSCI_Aluminum", "GSCI_Nickel"]]


gsci_df["Date"] = pd.to_datetime(gsci_df["Date"])
bbg_df = pd.merge_asof(bbg_df, gsci_df, on = "Date",direction = "forward", tolerance = pd.Timedelta('7 days'))

first_al_idx = bbg_df["Aluminum"].first_valid_index()
for idx in range(first_al_idx, bbg_df.index[0], -1):
    new_val = bbg_df.loc[idx, "Aluminum"] * (bbg_df.loc[idx-1, "GSCI_Aluminum"]/bbg_df.loc[idx, "GSCI_Aluminum"])
    bbg_df.loc[idx-1, "Aluminum"] = new_val

first_ni_idx = bbg_df["Nickel"].first_valid_index()
for idx in range(first_ni_idx, bbg_df.index[0], -1):
    new_val = bbg_df.loc[idx, "Nickel"] * (bbg_df.loc[idx-1, "GSCI_Nickel"]/bbg_df.loc[idx, "GSCI_Nickel"])
    bbg_df.loc[idx-1, "Nickel"] = new_val

bbg_df = bbg_df.drop(["GSCI_Aluminum", "GSCI_Nickel"], axis = 1)

# Conduct PCA
pc_crb_df = bbg_df[['Date', 'WTI', 'Heating_Oil', 'Natural_Gas', 'Corn', 'Soybeans',
       'Live_Cattle', 'Gold', 'Aluminum', 'Copper', 'Sugar', 'Cotton', 'Cocoa',
       'Coffee', 'Nickel', 'Wheat', 'Lean_Hogs', 'Orange_Juice', 'SI1 Comdty',
       'RBOB_Gasoline']].copy(deep = True).dropna()
data = pc_crb_df[['WTI', 'Heating_Oil', 'Natural_Gas', 'Corn', 'Soybeans',
       'Live_Cattle', 'Gold', 'Aluminum', 'Copper', 'Sugar', 'Cotton', 'Cocoa',
       'Coffee', 'Nickel', 'Wheat', 'Lean_Hogs', 'Orange_Juice', 'SI1 Comdty',
       'RBOB_Gasoline']].values
data = StandardScaler().fit_transform(data)

pca = PCA(n_components=1)
principal_components = pca.fit_transform(data)
pc_crb_df['CRB_PC'] = principal_components

loadings_crb = pd.DataFrame(pca.components_.T, columns = ["PC1"], index = ['WTI', 'Heating_Oil', 'Natural_Gas', 'Corn', 'Soybeans',
       'Live_Cattle', 'Gold', 'Aluminum', 'Copper', 'Sugar', 'Cotton', 'Cocoa',
       'Coffee', 'Nickel', 'Wheat', 'Lean_Hogs', 'Orange_Juice', 'SI1 Comdty',
       'RBOB_Gasoline'])
explained_variance_crb = pca.explained_variance_ratio_
print(explained_variance_crb)

bbg_df["CRB_PC"] = pc_crb_df["CRB_PC"]

# Keep only data at end of quarter
mask = [date.month%3 == 0 for date in bbg_df["Date"]]
bbg_df = bbg_df[mask]

bbg_df = bbg_df[["Date", "CRB_PC"]]

# Export Data
# bbg_df.to_excel("Bloomberg_Commodity_Data_Cleaned_Quarterly.xlsx", index = False)
