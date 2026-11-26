-- NVIDIA structured financials (FY1999-FY2026 annual, FY2000Q1-FY2027Q3 quarterly)
-- Amounts: USD millions. Shares: millions. EPS: USD/share. null = empty CSV field.
-- Portable DDL: runs as-is in SQLite and MySQL (REAL = DOUBLE in MySQL, TEXT dates kept as ISO strings).
-- Source of every row: NVDA-SEC-filings/<source_file> (accession column); see nvda_financials.json meta.

CREATE TABLE nvda_annual (
  fy INTEGER NOT NULL,
  period_end TEXT,
  filed TEXT,
  accession TEXT,
  source_file TEXT,
  source_form TEXT,
  derived INTEGER NOT NULL DEFAULT 0,
  revenue REAL,
  gross_profit REAL,
  operating_income REAL,
  net_income REAL,
  eps_diluted REAL,
  shares_diluted_m REAL,
  eps_as_reported REAL,
  shares_as_reported_m REAL,
  split_factor REAL,
  ocf REAL,
  capex REAL,
  fcf REAL,
  cash REAL,
  st_investments REAL,
  cash_st REAL,
  total_debt REAL,
  debt_source TEXT,
  quarter_sum_delta TEXT,
  note TEXT,
  PRIMARY KEY (fy)
);

CREATE TABLE nvda_quarterly (
  fy INTEGER NOT NULL,
  quarter INTEGER NOT NULL,
  period_end TEXT,
  filed TEXT,
  accession TEXT,
  source_file TEXT,
  source_form TEXT,
  derived INTEGER NOT NULL DEFAULT 0,
  revenue REAL,
  gross_profit REAL,
  operating_income REAL,
  net_income REAL,
  eps_diluted REAL,
  shares_diluted_m REAL,
  eps_as_reported REAL,
  shares_as_reported_m REAL,
  split_factor REAL,
  ocf REAL,
  capex REAL,
  fcf REAL,
  cash REAL,
  st_investments REAL,
  cash_st REAL,
  total_debt REAL,
  debt_source TEXT,
  ytd_revenue REAL,
  ytd_gross_profit REAL,
  ytd_operating_income REAL,
  ytd_net_income REAL,
  ytd_ocf REAL,
  ytd_capex REAL,
  ytd_eps REAL,
  note TEXT,
  PRIMARY KEY (fy, quarter)
);

-- ================= SQLite import =================
-- sqlite3 nvda.db < nvda_schema.sql
-- sqlite3 nvda.db ".mode csv" ".import --csv --skip 1 nvda_annual.csv nvda_annual" ".import --csv --skip 1 nvda_quarterly.csv nvda_quarterly"
-- then normalize empty strings to NULL (no-op where already NULL):
UPDATE nvda_annual SET period_end=NULLIF(period_end,''), filed=NULLIF(filed,''), accession=NULLIF(accession,''), source_file=NULLIF(source_file,''), source_form=NULLIF(source_form,''), revenue=NULLIF(revenue,''), gross_profit=NULLIF(gross_profit,''), operating_income=NULLIF(operating_income,''), net_income=NULLIF(net_income,''), eps_diluted=NULLIF(eps_diluted,''), shares_diluted_m=NULLIF(shares_diluted_m,''), eps_as_reported=NULLIF(eps_as_reported,''), shares_as_reported_m=NULLIF(shares_as_reported_m,''), split_factor=NULLIF(split_factor,''), ocf=NULLIF(ocf,''), capex=NULLIF(capex,''), fcf=NULLIF(fcf,''), cash=NULLIF(cash,''), st_investments=NULLIF(st_investments,''), cash_st=NULLIF(cash_st,''), total_debt=NULLIF(total_debt,''), debt_source=NULLIF(debt_source,''), quarter_sum_delta=NULLIF(quarter_sum_delta,''), note=NULLIF(note,'');
UPDATE nvda_quarterly SET period_end=NULLIF(period_end,''), filed=NULLIF(filed,''), accession=NULLIF(accession,''), source_file=NULLIF(source_file,''), source_form=NULLIF(source_form,''), revenue=NULLIF(revenue,''), gross_profit=NULLIF(gross_profit,''), operating_income=NULLIF(operating_income,''), net_income=NULLIF(net_income,''), eps_diluted=NULLIF(eps_diluted,''), shares_diluted_m=NULLIF(shares_diluted_m,''), eps_as_reported=NULLIF(eps_as_reported,''), shares_as_reported_m=NULLIF(shares_as_reported_m,''), split_factor=NULLIF(split_factor,''), ocf=NULLIF(ocf,''), capex=NULLIF(capex,''), fcf=NULLIF(fcf,''), cash=NULLIF(cash,''), st_investments=NULLIF(st_investments,''), cash_st=NULLIF(cash_st,''), total_debt=NULLIF(total_debt,''), debt_source=NULLIF(debt_source,''), ytd_revenue=NULLIF(ytd_revenue,''), ytd_gross_profit=NULLIF(ytd_gross_profit,''), ytd_operating_income=NULLIF(ytd_operating_income,''), ytd_net_income=NULLIF(ytd_net_income,''), ytd_ocf=NULLIF(ytd_ocf,''), ytd_capex=NULLIF(ytd_capex,''), ytd_eps=NULLIF(ytd_eps,''), note=NULLIF(note,'');

-- ================= MySQL import =================
-- Run the DDL above, then (LOCAL infile requires local_infile=1 on server and client):
-- MySQL> LOAD DATA LOCAL INFILE 'nvda_annual.csv' INTO TABLE nvda_annual FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES (fy,@period_end,@filed,@accession,@source_file,@source_form,derived,@revenue,@gross_profit,@operating_income,@net_income,@eps_diluted,@shares_diluted_m,@eps_as_reported,@shares_as_reported_m,@split_factor,@ocf,@capex,@fcf,@cash,@st_investments,@cash_st,@total_debt,@debt_source,@quarter_sum_delta,@note) SET period_end=NULLIF(@period_end,''), filed=NULLIF(@filed,''), accession=NULLIF(@accession,''), source_file=NULLIF(@source_file,''), source_form=NULLIF(@source_form,''), revenue=NULLIF(@revenue,''), gross_profit=NULLIF(@gross_profit,''), operating_income=NULLIF(@operating_income,''), net_income=NULLIF(@net_income,''), eps_diluted=NULLIF(@eps_diluted,''), shares_diluted_m=NULLIF(@shares_diluted_m,''), eps_as_reported=NULLIF(@eps_as_reported,''), shares_as_reported_m=NULLIF(@shares_as_reported_m,''), split_factor=NULLIF(@split_factor,''), ocf=NULLIF(@ocf,''), capex=NULLIF(@capex,''), fcf=NULLIF(@fcf,''), cash=NULLIF(@cash,''), st_investments=NULLIF(@st_investments,''), cash_st=NULLIF(@cash_st,''), total_debt=NULLIF(@total_debt,''), debt_source=NULLIF(@debt_source,''), quarter_sum_delta=NULLIF(@quarter_sum_delta,''), note=NULLIF(@note,'');
-- MySQL> LOAD DATA LOCAL INFILE 'nvda_quarterly.csv' INTO TABLE nvda_quarterly FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES (fy,quarter,@period_end,@filed,@accession,@source_file,@source_form,derived,@revenue,@gross_profit,@operating_income,@net_income,@eps_diluted,@shares_diluted_m,@eps_as_reported,@shares_as_reported_m,@split_factor,@ocf,@capex,@fcf,@cash,@st_investments,@cash_st,@total_debt,@debt_source,@ytd_revenue,@ytd_gross_profit,@ytd_operating_income,@ytd_net_income,@ytd_ocf,@ytd_capex,@ytd_eps,@note) SET period_end=NULLIF(@period_end,''), filed=NULLIF(@filed,''), accession=NULLIF(@accession,''), source_file=NULLIF(@source_file,''), source_form=NULLIF(@source_form,''), revenue=NULLIF(@revenue,''), gross_profit=NULLIF(@gross_profit,''), operating_income=NULLIF(@operating_income,''), net_income=NULLIF(@net_income,''), eps_diluted=NULLIF(@eps_diluted,''), shares_diluted_m=NULLIF(@shares_diluted_m,''), eps_as_reported=NULLIF(@eps_as_reported,''), shares_as_reported_m=NULLIF(@shares_as_reported_m,''), split_factor=NULLIF(@split_factor,''), ocf=NULLIF(@ocf,''), capex=NULLIF(@capex,''), fcf=NULLIF(@fcf,''), cash=NULLIF(@cash,''), st_investments=NULLIF(@st_investments,''), cash_st=NULLIF(@cash_st,''), total_debt=NULLIF(@total_debt,''), debt_source=NULLIF(@debt_source,''), ytd_revenue=NULLIF(@ytd_revenue,''), ytd_gross_profit=NULLIF(@ytd_gross_profit,''), ytd_operating_income=NULLIF(@ytd_operating_income,''), ytd_net_income=NULLIF(@ytd_net_income,''), ytd_ocf=NULLIF(@ytd_ocf,''), ytd_capex=NULLIF(@ytd_capex,''), ytd_eps=NULLIF(@ytd_eps,''), note=NULLIF(@note,'');
