# WRDSDownloadScripts

This repo contains IPython jupyter notebook scripts to download different datasets from WRDS.

## Requirements

* Python
* [Python WRDS downloader](https://pypi.org/project/wrds/)
* WRDS account

## Datasets

* TRACE Bond transaction data
    - intraday transaction data is very large
    - script computes daily statistics from intraday bond transactions and create a dataset at the bond-day level
* [Earnings Response Coefficients (ERC)](https://en.wikipedia.org/wiki/Earnings_response_coefficient): run `ERC script.ipynb`
    - script calculates earnings announcement returns, summary of analyst earnings forecasts and actual forecasts from IBES

## notes

- [Here](https://wrds-www.wharton.upenn.edu/pages/support/wrds-cloud/python-wrds-cloud/introduction-setup-python/) is a general guide on how to connect to WRDS with python
- WRDS server session: this approach is for when you want to get data *and compute stuff* on the WRDS server. It is possible to execute python scripts. But it was unclear to me how to execute SQL commands that include computations such as merges, as opposed to only selecting and downloading data.
    * `ssh USERNAME@wrds-cloud.wharton.upenn.edu` to login
    * `qrsh` to get into compute node