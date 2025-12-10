# station metadata
stations = {
    "001": "Safari Park-LHR",
    "002": "Kahna Nau Hospital-LHR",
    "003": "PKLI-LHR",
    "004": "FMDRC-LHR",
    "005": "UET-LHR",
    "006": "LWMC-LHR",
    "007": "Punjab University-LHR",
    "008": "Govt. Teaching Hospital Shahdara-LHR",
    "009": "DHQ Sheikhupura",
    "010": "Mobile 1",
    "011": "Mobile 2",
    "012": "Mobile 3",
    "013": "Mobile 4",
    "014": "Mobile 5",
    "015": "DC Office Faisalabad",
    "016": "GCU Faisalabad",
    "017": "NTU Faisalabad",
    "018": "GCW Gujranwala",
    "019": "DC Office Gujranwala",
    "020": "BZU Multan",
    "021": "IUB (Baghdad Campus) Bahawalpur",
    "022": "DC Office Sargodha",
    "023": "BISE Sargodha",
    "024": "DC Office Sialkot",
    "025": "IUB (Khawaja Fareed Campus) Bahawalpur",
    "026": "DC Office DG Khan",
    "027": "DC Office Rawalpindi",
    "028": "ARID University Rawalpindi",
    "029": "Drug Testing Laboratory Rawalpindi",
    "030": "M. Nawaz Sharif University of Engineering & Technology Multan",
    "031": "DC Office Kasur",
    "032": "DC Office Narowal",
    "033": "DC Office Hafizabad",
    "034": "DC Office Gujrat",
    "035": "DC Office Chakwal",
    "036": "DC Office Khanewal",
    "037": "DC Office Muzaffargarh",
    "038": "DC Office Rahim Yar Khan",
}

# station coordinates (lat, lng)
station_coordinates = {
    "Safari Park-LHR": {"lat": 31.382314774885888, "lng": 74.21817281534902},
    "Kahna Nau Hospital-LHR": {"lat": 31.370968642952125, "lng": 74.36509796071374},
    "PKLI-LHR": {"lat": 31.455944217196357, "lng": 74.4637726464879},
    "FMDRC-LHR": {"lat": 31.535903137206997, "lng": 74.43518804649057},
    "UET-LHR": {"lat": 31.579825674297712, "lng": 74.35500334094795},
    "LWMC-LHR": {"lat": 31.463797290721757, "lng": 74.22594175216207},
    "Punjab University-LHR": {"lat": 31.47965946421483, "lng": 74.26608653889994},
    "Govt. Teaching Hospital Shahdara-LHR": {"lat": 31.638126385663895, "lng": 74.28518245233634},
    "DHQ Sheikhupura": {"lat": 31.711907268506444, "lng": 73.97887262744989},
    "DC Office Faisalabad": {"lat": 31.425448762788633, "lng": 73.08115579440872},
    "GCU Faisalabad": {"lat": 31.416246064561182, "lng": 73.07000252883559},
    "NTU Faisalabad": {"lat": 31.462112827887097, "lng": 73.14854729999999},
    "GCW Gujranwala": {"lat": 32.25587012731105, "lng": 74.15945324463222},
    "DC Office Gujranwala": {"lat": 32.17468001795155, "lng": 74.19513105997787},
    "BZU Multan": {"lat": 30.262345863388603, "lng": 71.51253806752977},
    "M. Nawaz Sharif University of Engineering & Technology Multan": {"lat": 30.029109580383068, "lng": 71.54151150235819},
    "IUB (Baghdad Campus) Bahawalpur": {"lat": 29.376832580609566, "lng": 71.76267240237333},
    "IUB (Khawaja Fareed Campus) Bahawalpur": {"lat": 29.397708118736162, "lng": 71.69163577353685},
    "DC Office Sargodha": {"lat": 32.07161053848134, "lng": 72.67279475998042},
    "BISE Sargodha": {"lat": 32.0355877857731, "lng": 72.70063274138406},
    "DC Office Sialkot": {"lat": 32.50525590601202, "lng": 74.53303397614911},
    "DC Office DG Khan": {"lat": 30.051792633623844, "lng": 70.62966164154528},
    "DC Office Rawalpindi": {"lat": 33.58462459856753, "lng": 73.06891569999999},
    "ARID University Rawalpindi": {"lat": 33.65061773446243, "lng": 73.08067117116441},
    "Drug Testing Laboratory Rawalpindi": {"lat": 33.54226391435295, "lng": 73.01392021534237},
    "DC Office Kasur": {"lat": 31.11611, "lng": 74.46725},
    "DC Office Narowal": {"lat": 32.09704, "lng": 74.89411},
    "DC Office Hafizabad": {"lat": 32.07171, "lng": 73.71436},
    "DC Office Gujrat": {"lat": 32.58559, "lng": 74.07833},
    "DC Office Chakwal": {"lat": 32.92564, "lng": 72.80549},
    "DC Office Khanewal": {"lat": 30.30231, "lng": 71.92921},
    "DC Office Muzaffargarh": {"lat": 30.07608, "lng": 71.19038},
    "DC Office Rahim Yar Khan": {"lat": 28.42323, "lng": 70.31827}
}

# time intervals and table suffixes
intervals = {
    "05": "05_min",
    "15": "15_min",
    "30": "30_min",
    "60": "60_min",
    "1440": "1440_min"
}

# pollutant mapping
pollutants = [
    "O3", "CO", "SO2", "NO", "NO2", "NOX",
    "PM10", "PM2.5", "WS", "WD", "Temp", "RH", "BP", "Rain", "SR"
]

# Define breakpoint tables for PM2.5
pm25_breakpoints = [
    {"BPLo": 0, "BPHi": 15, "ILo": 0, "IHi": 50},
    {"BPLo": 15.1, "BPHi": 35, "ILo": 51, "IHi": 100},
    {"BPLo": 35.1, "BPHi": 70, "ILo": 101, "IHi": 150},
    {"BPLo": 70.1, "BPHi": 150, "ILo": 151, "IHi": 200},
    {"BPLo": 150.1, "BPHi": 250, "ILo": 201, "IHi": 300},
    {"BPLo": 250.1, "BPHi": 350, "ILo": 301, "IHi": 400},
    {"BPLo": 350.1, "BPHi": 350.1, "ILo": 401, "IHi": 500}
]

# PM10 Breakpoints
pm10_breakpoints = [
    {"BPLo": 0, "BPHi": 75, "ILo": 0, "IHi": 50},
    {"BPLo": 75.1, "BPHi": 150, "ILo": 51, "IHi": 100},
    {"BPLo": 150.1, "BPHi": 250, "ILo": 101, "IHi": 150},
    {"BPLo": 250.1, "BPHi": 350, "ILo": 151, "IHi": 200},
    {"BPLo": 350.1, "BPHi": 450, "ILo": 201, "IHi": 300},
    {"BPLo": 450.1, "BPHi": 550, "ILo": 301, "IHi": 400},
    {"BPLo": 550.1, "BPHi": 550.1, "ILo": 401, "IHi": 500}
]

# SO2 Breakpoints
so2_breakpoints = [
    {"BPLo": 0, "BPHi": 60, "ILo": 0, "IHi": 50},
    {"BPLo": 60.1, "BPHi": 120, "ILo": 51, "IHi": 100},
    {"BPLo": 120.1, "BPHi": 220, "ILo": 101, "IHi": 150},
    {"BPLo": 220.1, "BPHi": 320, "ILo": 151, "IHi": 200},
    {"BPLo": 320.1, "BPHi": 800, "ILo": 201, "IHi": 300},
    {"BPLo": 800.1, "BPHi": 1600, "ILo": 301, "IHi": 400},
    {"BPLo": 1600.1, "BPHi": 1600.1, "ILo": 401, "IHi": 500}
]

# NO2 Breakpoints
no2_breakpoints = [
    {"BPLo": 0, "BPHi": 40, "ILo": 0, "IHi": 50},
    {"BPLo": 40.1, "BPHi": 80, "ILo": 51, "IHi": 100},
    {"BPLo": 80.1, "BPHi": 130, "ILo": 101, "IHi": 150},
    {"BPLo": 130.1, "BPHi": 180, "ILo": 151, "IHi": 200},
    {"BPLo": 180.1, "BPHi": 380, "ILo": 201, "IHi": 300},
    {"BPLo": 380.1, "BPHi": 580, "ILo": 301, "IHi": 400},
    {"BPLo": 580.1, "BPHi": 580.1, "ILo": 401, "IHi": 500}
]

# O3 Breakpoints
o3_breakpoints = [
    {"BPLo": 0, "BPHi": 65, "ILo": 0, "IHi": 50},
    {"BPLo": 65.1, "BPHi": 130, "ILo": 51, "IHi": 100},
    {"BPLo": 130.1, "BPHi": 195, "ILo": 101, "IHi": 150},
    {"BPLo": 195.1, "BPHi": 260, "ILo": 151, "IHi": 200},
    {"BPLo": 260.1, "BPHi": 450, "ILo": 201, "IHi": 300},
    {"BPLo": 450.1, "BPHi": 550, "ILo": 301, "IHi": 400},
    {"BPLo": 550.1, "BPHi": 550.1, "ILo": 401, "IHi": 500}
]

# CO Breakpoints
co_breakpoints = [
    {"BPLo": 0, "BPHi": 2.5, "ILo": 0, "IHi": 50},
    {"BPLo": 2.6, "BPHi": 5, "ILo": 51, "IHi": 100},
    {"BPLo": 5.1, "BPHi": 7.5, "ILo": 101, "IHi": 150},
    {"BPLo": 7.6, "BPHi": 10, "ILo": 151, "IHi": 200},
    {"BPLo": 10.1, "BPHi": 25, "ILo": 201, "IHi": 300},
    {"BPLo": 25.1, "BPHi": 40, "ILo": 301, "IHi": 400},
    {"BPLo": 40.1, "BPHi": 40.1, "ILo": 401, "IHi": 500}
]

# Map pollutants to their breakpoint tables for AQI calculation
pollutant_breakpoints = {
    "PM25": pm25_breakpoints,
    "PM10": pm10_breakpoints,
    "SO2": so2_breakpoints,
    "NO2": no2_breakpoints,
    "O3": o3_breakpoints,
    "CO": co_breakpoints,
}

# Define AQI categories
aqi_categories = [
    {"range": [0, 50], "category": "Good"},
    {"range": [51, 100], "category": "Satisfactory"},
    {"range": [101, 150], "category": "Moderate"},
    {"range": [151, 200], "category": "Unhealthy for sensitive group"},
    {"range": [201, 300], "category": "Unhealthy"},
    {"range": [301, 400], "category": "Very Unhealthy"},
    {"range": [401, 500], "category": "Hazardous"}
]

conversion_factors = {
    "PM25": 1.0,              # already in µg/m³
    "PM10": 1.0,              # already in µg/m³
    "SO2": 2.6315789473684212,  # 1 µg/m³ = 0.38 ppb → µg/m³ = ppb / 0.38
    "NO": 1.2195121951219512,   # 1 µg/m³ = 0.82 ppb → µg/m³ = ppb / 0.82
    "NOX": 1.8867924528301887,  # 1 µg/m³ = 0.53 ppb → µg/m³ = ppb / 0.53
    "NO2": 1.8867924528301887,  # 1 µg/m³ = 0.53 ppb → µg/m³ = ppb / 0.53
    "O3": 1.9607843137254901,   # 1 µg/m³ = 0.51 ppb → µg/m³ = ppb / 0.51
    "CO": 1.1494252873563218,   # 1 mg/m³ = 0.87 ppm → mg/m³ = ppm / 0.87
}

# Optional min/max thresholds per pollutant for alerting. Leave empty to disable.
threshold_limits = {
    "PM25": {"min": 0, "max": 2000},
    "PM10": {"min": 0, "max": 2000},
    "CO": {"min": 0, "max": 230},
    "SO2": {"min": 0, "max": 5263},
    "NO2": {"min": 0, "max": 3773},
    "O3": {"min": 0, "max": 3921},
}
