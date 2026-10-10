from dukascopy_python import fetch, INTERVAL_MIN_1, INTERVAL_HOUR_1, instruments, OFFER_SIDE_ASK, OFFER_SIDE_BID

def fetch_data(start_date, end_date, instrument = instruments.INSTRUMENT_VCCY_BTC_USD):

    print("\n\n", "=" * 70)
    print(F"INITIALIZING DATA FETCH FOR INSTRUMENT: {instrument}")
    print("=" * 70, "\n\n")

    try:
        #fetching hourly and m5 data which is not optimal. will make efficient after proof of concept

        bid_h1 = fetch(instrument, INTERVAL_HOUR_1, OFFER_SIDE_BID,start_date, end_date)
        ask_h1 = fetch(instrument, INTERVAL_HOUR_1, OFFER_SIDE_ASK,start_date, end_date)

        bid_m5 = fetch(instrument, INTERVAL_MIN_1, OFFER_SIDE_BID, start_date, end_date)
        ask_m5 = fetch(instrument, INTERVAL_MIN_1, OFFER_SIDE_ASK, start_date, end_date)

    except Exception as e:
        print("/"* 70)
        print(f"DATA FETCH FAILED. KINDLY CHECK YOUR INTERNET CONNECTION OR YOUR FETCH LOGIC.{e}")
        print("/"* 70, "\n\n")
        
        return "\n\n=== OPERATION STOPPED ==="
    
    print("=" * 70)
    print(F"DATA FETCHED SUCCESSFULLY\n\nINSTRUMENT: {instrument}\nSTART DATE: {start_date}\nEND DATE: {end_date}\n\n")
    print("=" * 70, "\n\n")

    print("=" * 70)
    print(F"AGGREGATING DATA TO FORM CANDLES")
    print("=" * 70, "\n\n")

    return bid_h1, ask_h1, bid_m5, ask_m5
   