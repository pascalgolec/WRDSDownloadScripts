# WRDSDownloadScripts

This repo contains IPython jupyter notebook scripts to download specific big datasets from WRDS and calculate statistics at a more aggregated level. A naive query is not possible due to massive amounts of data (e.g. intraday bond transactions of 1GB per day) at a disaggregated level. The scripts breaks up the queries into manageable chunks and perform a loop.

## Requirements

* Python
* [Python WRDS downloader](https://pypi.org/project/wrds/)
* WRDS account

## Datasets

* TRACE Bond intraday transaction data: run `TRACE.ipynb`
    - script computes daily statistics from intraday bond transactions and create a dataset at the bond-day level
* Calculate [earnings Response Coefficients (ERC)](https://en.wikipedia.org/wiki/Earnings_response_coefficient): run `ERC script.ipynb`
    - script computes the necessary variables to calculate ERC's: earnings announcement returns, summary of analyst earnings forecasts and actual forecasts from IBES

## personal notes

- [Here](https://wrds-www.wharton.upenn.edu/pages/support/wrds-cloud/python-wrds-cloud/introduction-setup-python/) is a general guide on how to connect to WRDS with python
- WRDS server session: this approach is for when you want to get data *and compute stuff* on the WRDS server. It is possible to execute python scripts. But it is unclear to me how to execute SQL commands that include computations such as merges, as opposed to only selecting and downloading data.
    * `ssh USERNAME@wrds-cloud.wharton.upenn.edu` to login
    * `qrsh` to get into compute node
