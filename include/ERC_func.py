# function gets all the variables for a given data range
def get_dferc(db, mindate, maxdate, jointype, dfccm_linktable, dfdsenames, dfibesident, df_sic, df_ff49_ret):

    import datetime
    import pandas as pd

    # convenience variables
    diff1d = datetime.timedelta(days=1)
    diff2d = datetime.timedelta(days=1)
    diff5d = datetime.timedelta(days=5)
    diff45d = datetime.timedelta(days=45)

    ###################################################
    # get the earnings announcement dates from compustat
    ###################################################
    query = str("""select gvkey, rdq, datadate, prccq
    				FROM comp.fundq
    				WHERE rdq > '{!s}' and rdq < '{!s}'
    				and indfmt='INDL' and datafmt='STD' and popsrc='D' and consol='C' """).format(mindate, maxdate)

    dfrdq = db.raw_sql(query)

    # keep only those firmquarters that were reported within 90 days after quarter's end
    dfrdq = dfrdq[dfrdq['rdq'] - dfrdq['datadate'] <= datetime.timedelta(90)]

    # drop duplicates, keep first observation that is duplicate (in guide they keep none actually)
    dfrdq = dfrdq[~dfrdq.duplicated(keep='first')]

    #######################
    # merge data with permno
    #######################
    out = pd.merge(dfrdq, dfccm_linktable, how=jointype, on='gvkey', 
    		left_index=False, right_index=False, sort=False,
    		suffixes=('_x', '_y'), copy=True, indicator=False)
    out.set_index(['gvkey', 'rdq'])

    # change 'None' in linkenddt to todays date
    today = datetime.date.today()
    out['linkenddt'] = out['linkenddt'].fillna(today)
    out['linkdt'] = out['linkdt'].fillna(datetime.date(1900, 1, 1))

    # announcement date (rdq) must be between linkdt and linkenddt: a.linkdt <= b.rdq <= linkenddt
    out = out.loc[(out['linkdt'] <= out['rdq']) & (out['rdq'] <= out['linkenddt'])]

    # linktype is in ("LC" "LN" "LU" "LX" "LD" "LS")
    out = out[out['linktype'].isin(("LC", "LN", "LU", "LX", "LD", "LS"))]

    # linkprim is in ("C", "P")
    out = out[out['linkprim'].isin(("C", "P"))]

    dfccmerged = out


    #################
    # merge with cusip
    #################
    out = pd.merge(dfccmerged, dfdsenames, how=jointype, left_on=['lpermno'], right_on=['permno'],
             left_index=False, right_index=False, sort=False,
             suffixes=('_x', '_y'), copy=True, indicator=False)
    out.set_index(['gvkey', 'rdq']);

    out.drop(columns=['permno'], inplace=True)

    # date must be between namedt and namendt
    out = out.loc[(out['namedt'] <= out['datadate']) & (out['datadate'] <= out['nameendt'])]

    dfccmerged = out


    #################
    # merge with IBES identification (idsum)
    #################
    out = pd.merge(dfccmerged, dfibesident, how=jointype, left_on=['ncusip'], right_on=['cusip'],
             left_index=False, right_index=False, sort=False,
             suffixes=('_x', '_y'), copy=True, indicator=False)
    out.drop(columns=['cusip'], inplace=True)

    out.set_index(['gvkey', 'rdq']);

    out = out.loc[out['rdq'] > out['sdates']]

    # drop duplicates with multiple sdates
    out = out.drop(['sdates'], axis=1)
    out = out[~out.duplicated(keep='last')]

    dfccmerged = out


    ##################################
    # analyst earnings forecast
    ##################################
    query = str("""SELECT ticker, statpers, meanest, fpedats
            FROM ibes.statsumu_epsus
            WHERE measure='EPS' and fiscalp='QTR' and fpi='6'
                and statpers > '{!s}' and statpers < '{!s}' """).format(mindate, maxdate)
    dfibesfc = db.raw_sql(query)

    out = pd.merge(dfccmerged, dfibesfc, how=jointype, left_on=['ibes_ticker'], right_on=['ticker'],
             left_index=False, right_index=False, sort=False,
             suffixes=('_x', '_y'), copy=True, indicator=False)
    out.drop(columns=['ticker'], inplace=True)

    out.set_index(['gvkey', 'rdq']);
    out = out.loc[(out['rdq']-diff45d < out['statpers']) & (out['statpers'] < out['rdq']-diff2d)] # may have multiple forecasts in this time window
    out = out.loc[(out['datadate']-diff5d <= out['fpedats']) & (out['datadate'] <= out['rdq']+diff5d)]

    out = out.drop_duplicates(subset=['gvkey', 'datadate'], keep='last', inplace=False)

    dfccmerged = out



    ##################################
    # merge with IBES actuals
    ##################################
    query = ("""SELECT value as actual, ticker, pends
            FROM ibes.actu_epsus
            WHERE measure='EPS' and pdicity='QTR'
                and pends > '{!s}' and pends < '{!s}' """).format(mindate-diff45d, maxdate+diff45d)
    ibesdata = db.raw_sql(query)

    out = pd.merge(dfccmerged, ibesdata, how=jointype, left_on=['ibes_ticker'], right_on=['ticker'],
             left_index=False, right_index=False, sort=False,
             suffixes=('_x', '_y'), copy=True, indicator=False)
    out.drop(columns=['ticker'], inplace=True)

    out.set_index(['gvkey', 'rdq']);
    out = out.loc[(out['pends']-diff5d < out['datadate']) & (out['datadate'] < out['pends']+diff5d)]

    dfccmerged = out


    ##################################
    # merge with stock returns
    ##################################

    ##################################
    # FF 49 industry returns
    query = str("""SELECT permno, date, ret, hsiccd
        FROM crsp.dsf
        WHERE date > '{!s}' and date < '{!s}' 
        LIMIT 10000000""").format(mindate-diff45d-diff5d, maxdate+diff5d)

    dfstockreturns_dsf = db.raw_sql(query)

    # merge returns
    out = pd.merge(dfccmerged, dfstockreturns_dsf, how=jointype, left_on=['lpermno'], right_on=['permno'],
		left_index=False, right_index=False, sort=False,
		suffixes=('_x', '_y'), copy=True, indicator=False)
    out.drop(columns=['permno'], inplace=True)

    out.set_index(['gvkey', 'rdq']);
    out = out.loc[(out['date']-diff1d <= out['rdq']) & (out['rdq'] <= out['date']+diff1d)]
    dfccmerged = out

    # merge with sic link table
    dfccmerged['unitkey'] = 1
    out = pd.merge(dfccmerged, df_sic, how='outer', on=['unitkey'], copy=True)

    out = out.loc[(out['sic1'] <= out['hsiccd']) & (out['hsiccd'] <= out['sic2'])]

    out.drop(columns=['sic1', 'sic2', 'unitkey'], inplace=True)

    # merge with FF 49 industry returns
    # select the relevant of FF 49 industry returns
    df_ff49_ret_select = df_ff49_ret.loc[(mindate-diff2d <= df_ff49_ret['date']) & (df_ff49_ret['date'] <= maxdate+diff2d)]

    # turn columns into rows
    df_ff49_ret_select = pd.melt(df_ff49_ret_select, id_vars=['date'])

    df_ff49_ret_select.rename(columns={'variable': 'ff49_str'}, inplace=True)

    # FF returns are in percent
    df_ff49_ret_select['value'] = df_ff49_ret_select['value']/100

    # merge industry returns with dataframe
    outtest = pd.merge(out, df_ff49_ret_select, how='left', on=['ff49_str'], copy=True, suffixes=('_x', '_y'))

    outtest['date_x'] = pd.to_datetime(outtest['date_x'])

    outtest = outtest.loc[outtest['date_x']==outtest['date_y']]
    outtest.rename(columns={'date_x': 'date', 'value': 'ret_ff49ind'}, inplace=True)
    outtest.drop(columns=['date_y'], inplace=True)

    dfccmerged = outtest

	##################################
    # decile returns
    query = str("""SELECT permno, date, decret, capn
            FROM crsp.erdport1
            WHERE date > '{!s}' and date < '{!s}' 
            LIMIT 5000000""").format(mindate-diff45d-diff5d, maxdate+diff5d)

    dfstockreturns_dec = db.raw_sql(query)

    ###################################
    # get abnormal announcement returns
    out = pd.merge(dfccmerged, dfstockreturns_dec, how=jointype, left_on=['lpermno'], right_on=['permno'],
             left_index=False, right_index=False, sort=False,
             suffixes=('_x', '_y'), copy=True, indicator=False)
    out.drop(columns=['permno'], inplace=True)
    out.drop(columns=['date_x'], inplace=True)
    out.rename(columns={'date_y': 'date'}, inplace=True)

    out.set_index(['gvkey', 'rdq']);
    out = out.loc[(out['date']-diff1d <= out['rdq']) & (out['rdq'] <= out['date']+diff1d)]

    dfccmerged = out

    grouped = out.groupby(['gvkey', 'rdq'])

    dfcar = grouped.agg({'ret':'sum', 'decret':'sum', 'ret_ff49ind':'sum'}).reset_index() # need reset index so that it retains the keys
    dfcar['cumulative_ret']= dfcar['ret']
    dfcar['car_dec']= dfcar['ret'] - dfcar['decret']
    dfcar['car_ff49ind']= dfcar['ret'] - dfcar['ret_ff49ind']
    dfcar = dfcar.drop(['ret', 'decret', 'ret_ff49ind'], axis=1)

    out = pd.merge(dfccmerged, dfcar, how=jointype, on=['gvkey', 'rdq'],
             left_index=False, right_index=False, sort=False,
             suffixes=('_x', '_y'), copy=True, indicator=False)
    out.set_index(['gvkey', 'rdq']);

    out.drop_duplicates(subset=['gvkey', 'rdq'], keep='last', inplace=True)
    out.drop(columns=['ret', 'decret', 'ret_ff49ind', 'date'], inplace=True)

    dfccmerged = out

    ##################################
    # get cumulative pre-announcement return
    out = pd.merge(dfccmerged, dfstockreturns_dsf, how=jointype, left_on=['lpermno'], right_on=['permno'],
             left_index=False, right_index=False, sort=False,
             suffixes=('_x', '_y'), copy=True, indicator=False)
    out.drop(columns=['permno'], inplace=True)

    out.set_index(['gvkey', 'rdq']);
    out = out.loc[(out['statpers']+diff1d <= out['date']) & (out['date'] <= out['rdq'] - diff2d)]

    out['gross_ret'] = 1+out['ret']

    grouped = out.groupby(['gvkey', 'rdq'])
    dfpreannreturn = grouped.agg({'gross_ret':'prod'}).reset_index() # need reset index so that it retains the keys
    dfpreannreturn = dfpreannreturn.rename(columns={'gross_ret': 'preAnnRet'})


    out = pd.merge(dfccmerged, dfpreannreturn, how=jointype, on=['gvkey', 'rdq'],
             left_index=False, right_index=False, sort=False,
             suffixes=('_x', '_y'), copy=True, indicator=False)

    dfccmerged = out

    return dfccmerged

