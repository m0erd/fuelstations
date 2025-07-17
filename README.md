# 🛣️ Route Planner API with Cost-Optimized Fuel Stops

## 🚀 Overview
This is a geospatially intelligent **route planning API** built with Django 3.2.23. It computes the **optimal driving path** between two U.S. locations and intelligently selects the most **cost-effective fuel stops** along the way using real-world data.

### 🔍 Key Capabilities
- Uses the **geodesic formula** to compute real-world distances between fuel stations and route geometry
- Determines **cheapest fuel stations** within range intervals (500 miles max per tank)
- Minimizes fuel cost by evaluating multiple fuel options within detour constraints
- Returns an **interactive map URL** (from a free routing API)
- Reports **total fuel cost**, assuming 10 miles per gallon

---

## ⚙️ Tech Stack
- **Backend Framework:** Django 3.2.23
- **API Layer:** Django REST Framework
- **Routing API:** OpenRouteService (or equivalent free map API)
- **Geospatial Computation:** `geopy.distance.geodesic` for great-circle distance calculations
- **Fuel Data Source:** PostgreSql database with fuel station prices and coordinates
- **Demo Tools:** Postman for API testing, Loom for video walkthrough

---

## 🔁 How It Works

1. Accepts a `start` and `end` U.S. location from the user
2. Calls a routing API to get the full route geometry
3. Segments the route into 500-mile legs (vehicle’s max range)
4. For each segment:
   - Queries the PostgreSQL database for fuel stations located within a geospatial bounding box around the current leg
   - Filters nearby fuel stations using **latitude/longitude bounding boxes**
   - Computes actual distance using **geodesic calculations**
   - Selects the **cheapest station** within fuel range
6. Returns selected fuel stops, map URL, and total cost

---

## 📦 API Endpoint

### `POST /api/route/`

**Request Example:**
```json
{
  "start": "Los Angeles, CA",
  "end": "Denver, CO"
}


---

### ⚠️ Disclaimer
> **Note:** The version of the project shared here is intended for **demonstration purposes only**. While it illustrates the core functionality and logic — including route planning, geodesic distance calculations, and fuel optimization — certain aspects (e.g., **accuracy of calculations**) have been simplified for clarity and time constraints **on purpose**.

