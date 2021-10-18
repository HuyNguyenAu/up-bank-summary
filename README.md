# Up Bank Summary
A simple to tool to view the amount of money going in, out, and saved for each month.

## Requirements
- Python 3

## Setup
Rename `.api_key.example` to `.api_key` and replace the contents of the file with the API key you got from https://developer.up.com.au/#getting-started.

## Usage
Run the script:
```
$ python main.py
Fetching new transactions...
Fetched 10 new transactions.
Getting summary...
Year   Month   Money Saved   Money In   Money Out  
2021   Oct     2026.74       4849.56    2822.82    
2021   Sep     1241.62       13671.92   12430.3    
2021   Aug     1374.1        5100.98    3726.88    
2021   Jul     -7217.37      3566.27    10783.64   
2021   Jun     2401.31       8408.05    6006.74    
2021   May     8243.41       20578.24   12334.83   
2021   Apr     8537.79       11863.74   3325.95    
2021   Feb     10.0          10.0       0   
```

## Why
I wanted a simple and portable program that simply calculates how much I saved for each month of the year.

## Why didn't you separate the SQL queries from the code?
I wanted a single self contained script that I can easily move around.
