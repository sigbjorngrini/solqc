# Import class 
from solqc.bioforskstation import BioforskStation

# Create Bioforsk station
station = BioforskStation('Aas')

# Automatic tests
station.flag_offset()
station.zero_out()
station.missing_values()
station.flag_U1()
station.flag_U2()
station.flag_L1()
station.flag_L2()
station.flag_difference()
station.flag_consistency()

# Perform visual control
visual_control_dates = [['1995-05-25', '1995-05-25']]

# Get average year
avg_year = station.get_average_year(visual_control_dates)

# Get monthly averages
avg_year.resample('D', how='sum').resample('M')