# Air Quality API

## Base URL

- Use `https://api.epd-aqms-pk.com`
- All endpoints require API key authentication and return JSON.

## Authentication

All endpoints require an API key. Provide the key using one of these methods:

### Method 1: Header (Recommended)

```bash
X-API-Key: your-api-key-here
```

### Method 2: Query Parameter

```bash
?api_key=your-api-key-here
```

**Note**: Contact the API administrator to obtain your API key.

### Authentication Errors

- **401 Unauthorized**: Missing or invalid API key

  ```json
  { "error": "Unauthorized: invalid API key" }
  ```

- **500 Server Error**: API key not configured on server
  ```json
  { "error": "Server API key not configured" }
  ```

### Conventions

- **Datetime format**: `YYYY-MM-DD HH:MM:SS`
- **Intervals**: `05` (5 min), `15` (15 min), `30` (30 min), `60` (hourly), `1440` (daily)
- **Station name matching**: paths with `{station_name}` must be URL-encoded and match exactly (case and spaces).

---

### GET `/daily`

- **Purpose**: Hourly readings for the current day (00:00 to now) for every station.
- **Response**: Object keyed by station name → array of readings (chronological asc).

### GET `/monthly`

- **Purpose**: Daily readings for the current calendar month (1st to today) for every station.
- **Response**: Object keyed by station name → array of readings (chronological asc).

### GET `/aqi`

- **Purpose**: Latest AQI (max across pollutants with breakpoints) per station.
- **Response**: Object keyed by station name → `{ Date_Time, AQI, AQI_category, Dominant_Pollutant }` or `{ error }`.

### GET `/latest_hour`

- **Purpose**: Most recent hourly reading per station (single reading each).
- **Response**: Object keyed by station name → latest reading fields subset plus `{ AQI, AQI_category, Dominant_Pollutant }` when available.

### GET `/periodic`

- **Purpose**: Readings for every station over a time window at a specified interval.
- **Query params**:
  - `start_datetime` (required): `YYYY-MM-DD HH:MM:SS`
  - `end_datetime` (required): `YYYY-MM-DD HH:MM:SS`
  - `interval` (optional): one of `05, 15, 30, 60, 1440` (default `60`)
- **Response**: Object keyed by station name → array of readings within the window.

### GET `/coordinates`

- **Purpose**: Returns geographic coordinates (latitude and longitude) for all stations.
- **Response**: Object keyed by station name → `{ lat: number, lng: number }`.
- **Example response**:

  ```json
  {
    "Safari Park-LHR": { "lat": 31.382314774885888, "lng": 74.21817281534902 },
    "UET-LHR": { "lat": 31.579825674297712, "lng": 74.35500334094795 },
    ...
  }
  ```

---

### Station-specific endpoints

Use exact station name in the path (URL-encoded if it contains spaces or special chars).

### GET `/daily/{station_name}`

- Hourly readings for the current day (00:00 to now) for the station.

### GET `/monthly/{station_name}`

- Daily readings for the current calendar month (1st to today) for the station.

### GET `/periodic/{station_name}`

- Same as `/periodic`, but for a single station.
- Query params: `start_datetime`, `end_datetime`, `interval` (same rules).

### GET `/aqi/{station_name}`

- Latest AQI (max across pollutants) for the station.

---

### Reading object shape (typical)

Each reading may include:

```json
{
  "Date_Time": "2025-09-28 14:00:00",
  "O3": 62.4,
  "CO": 0.8,
  "SO2": 12.1,
  "NO": 8.2,
  "NO2": 24.5,
  "NOX": 41.7,
  "PM10": 86,
  "PM25": 54,
  "WS": 2.3,
  "WD": 180,
  "Temp": 31.6,
  "RH": 48.2,
  "BP": 1006.4,
  "Rain": 0,
  "SR": 612,
  "AQI": 153,
  "AQI_category": "Unhealthy",
  "Dominant_Pollutant": "PM25"
}
```

Example with error/sentinel values:

```json
{
  "Date_Time": "2025-09-28 14:00:00",
  "O3": "analyzer comm. error",
  "CO": "analyzer error",
  "PM25": "Invalid",
  "AQI": null,
  "AQI_category": null,
  "Dominant_Pollutant": null
}
```

Notes:

- Sentinel/error values are mapped as:
- Unit conversion: For stations `001`–`009`, pollutant values are converted to units used by AQI breakpoints (O3/SO2/NO/NO2/NOX in µg/m³; CO in mg/m³). Stations `010+` are already in those units. PM25/PM10 are always in µg/m³.
- Arrays returned by `/daily` and `/monthly` are sorted ascending by `Date_Time`.

---

### Alerts

The system automatically monitors data quality and generates alerts for various conditions. Alerts are stored in the database with timestamps and are available via REST API and real-time WebSocket.

#### Alert Types

The following alert types are automatically generated:

**Data Quality Alerts:**

- **E03**: Missing data samples (< 75%) - Less than 45 values in 1 hour average
- **E04.1**: No Data from Analyzer - Communication error with analyzer
- **E04.2**: No Data from Dust Analyzer - Analyzer error
- **E04.3**: No Data from Station - No hourly data received from station
- **E05**: Range Below Threshold - Pollutant value falls below minimum threshold
- **E06**: Range Beyond Threshold - Pollutant value exceeds maximum threshold

**Anomaly Detection Alerts:**

- **E07**: Spike/Abrupt Changes - Detects >300% change between consecutive hourly readings
- **E08**: Choking/Sticking - Detects when identical readings persist for 2+ consecutive hours

**Alert Schedule:**

- Sentinel & Threshold checks: Every hour at minute 5
- Spike/Abrupt changes: Every hour at minute 7
- Missing data checks: Every hour at minute 10
- Choking/Sticking checks: Every hour at minute 12

**Deduplication:**
All alerts use timestamp-based deduplication. An alert for the same condition and data timestamp (±1 minute) will not be recreated, preventing duplicate alerts for historical data.

#### GET `/alerts/recent`

- **Purpose**: Latest alerts emitted by the system.
- **Response**: Array of `{ Date_Time, Alert }`, newest first (up to 100).
- **Example response**:
  ```json
  [
    {
      "Date_Time": "2025-10-21 14:00:00",
      "Alert": "E07: Spike/Abrupt Changes for PM25 at UET-LHR at 2025-10-21 14:00:00"
    },
    {
      "Date_Time": "2025-10-21 13:00:00",
      "Alert": "E06: PM10 Range Beyond Threshold (2000) for Safari Park-LHR"
    }
  ]
  ```

#### GET `/alerts/last_two_days`

- **Purpose**: Alerts from the start of previous day up to now.
- **Response**: Array of `{ Date_Time, Alert }`, newest first.

#### GET `/alerts/range`

- **Purpose**: Alerts within a custom datetime range.
- **Query params**: `start_datetime`, `end_datetime` in `YYYY-MM-DD HH:MM:SS`.
- **Response**: Array of `{ Date_Time, Alert }`, newest first.

#### Realtime (Socket.IO)

- **Channel**: `alert`
- **Payload**: `{ Date_Time: string, Alert: string }`
- Connect to the API origin using Socket.IO (WebSocket transport preferred).
- New alerts are pushed immediately as they are generated.

---

### Examples

All examples use the header method for authentication. Replace `YOUR_API_KEY` with your actual API key.

Fetch periodic data for all stations hourly over a 24h window:

```bash
curl "https://api.epd-aqms-pk.com/periodic?start_datetime=2025-09-01%2000:00:00&end_datetime=2025-09-02%2000:00:00&interval=60" \
  -H "X-API-Key: YOUR_API_KEY"
```

Fetch AQI for a single station (URL-encoded name example `UET-LHR` needs no encoding):

```bash
curl "https://api.epd-aqms-pk.com/aqi/UET-LHR" \
  -H "X-API-Key: YOUR_API_KEY"
```

Fetch periodic data for a single station with spaces in name:

```bash
curl "https://api.epd-aqms-pk.com/periodic/IUB%20(Baghdad%20Campus)%20Bahawalpur?start_datetime=2025-09-01%2000:00:00&end_datetime=2025-09-01%2012:00:00&interval=60" \
  -H "X-API-Key: YOUR_API_KEY"
```

Fetch recent alerts:

```bash
curl "https://api.epd-aqms-pk.com/alerts/recent" \
  -H "X-API-Key: YOUR_API_KEY"
```

Fetch station coordinates:

```bash
curl "https://api.epd-aqms-pk.com/coordinates" \
  -H "X-API-Key: YOUR_API_KEY"
```

Alternative: Using query parameter instead of header:

```bash
curl "https://api.epd-aqms-pk.com/aqi/UET-LHR?api_key=YOUR_API_KEY"
```

---

### Available station names

Use exactly one of the following as `{station_name}`:

- Safari Park-LHR
- Kahna Nau Hospital-LHR
- PKLI-LHR
- FMDRC-LHR
- UET-LHR
- LWMC-LHR
- Punjab University-LHR
- Govt. Teaching Hospital Shahdara-LHR
- DHQ Sheikhupura
- Mobile 1
- Mobile 2
- Mobile 3
- Mobile 4
- Mobile 5
- DC Office Faisalabad
- GCU Faisalabad
- NTU Faisalabad
- GCW Gujranwala
- DC Office Gujranwala
- BZU Multan
- IUB (Baghdad Campus) Bahawalpur
- DC Office Sargodha
- BISE Sargodha
- DC Office Sialkot
- IUB (Khawaja Fareed Campus) Bahawalpur
- DC Office DG Khan
- DC Office Rawalpindi
- ARID University Rawalpindi
- Drug Testing Laboratory Rawalpindi
- M. Nawaz Sharif University of Engineering & Technology Multan
- DC Office Kasur
- DC Office Narowal
- DC Office Hafizabad,
- DC Office Gujrat,
- DC Office Chakwal,
- DC Office Khanewal,
- DC Office Muzaffargarh,
- DC Office Rahim Yar Khan,

If a station name is not recognized, the API returns `{ "error": "Station '<name>' not found" }`.
