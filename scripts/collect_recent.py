"""Collect a recent window for review, without rebuilding published tables."""
from datetime import datetime,timedelta
from pipeline import collect,config
from pipeline.dates import IST

def main():
    config.END=datetime.now(IST).date()
    config.START=config.END-timedelta(days=14)
    collect.main()

if __name__=='__main__': main()
