# Trip Planner: Complete Guide

Welcome to the Trip Planner application! This guide will walk you through how to use the app, its features, and some tips to make the most of your trip planning experience.

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Features](#features)
4. [How to Use](#how-to-use)
5. [Exporting to Google Maps](#exporting-to-google-maps)
6. [Tips and Tricks](#tips-and-tricks)
7. [Troubleshooting](#troubleshooting)
8. [Contributing](#contributing)

## Introduction

The Trip Planner is a web-based application that helps you plan your trips by optimizing the route between multiple locations. It uses the Google Maps API to calculate distances and provide directions, ensuring you have the most efficient journey possible.

## Getting Started

To use the Trip Planner, you'll need:

1. Python 3.7 or higher installed on your computer
2. Git (optional, for cloning the repository)
3. A Google Maps API key

## Installation

1. Clone the repository or download the source code:
   ```
   git clone https://github.com/your-username/trip-planner.git
   ```
   Or download and extract the ZIP file from the GitHub repository.

2. Navigate to the project directory:
   ```
   cd trip-planner
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up your Google Maps API key:
   - Create a `.env` file in the project root directory
   - Add your API key to the file:
     ```
     GOOGLE_MAPS_API_KEY=your_api_key_here
     ```

5. Run the Streamlit app:
   ```
   streamlit run Trip_Planner.py
   ```

6. Open your web browser and go to `http://localhost:8501` to use the Trip Planner.

## Features

- Plan trips with up to 10 locations
- Support for multiple countries and regions
- Optimized route calculation using the Traveling Salesman Problem (TSP) algorithm
- Interactive map display of your route
- Multiple transportation modes (driving, walking, bicycling, transit)
- Export your route to Google Maps for mobile use

## How to Use

1. **Select your trip area:**
   - Choose a country from the dropdown list
   - Enter the region or state within the selected country
   - Specify the city for your trip

2. **Enter locations:**
   - Input up to 10 locations you want to visit
   - Each location should be a specific place (e.g., "Eiffel Tower" rather than just "Paris")

3. **Generate the map:**
   - Click the "Generate Map" button
   - Select your preferred mode of transport
   - Wait for the application to calculate the optimal route

4. **View your optimized route:**
   - The map will display with numbered markers for each location
   - Blue lines show the route between locations
   - Each leg of the journey includes estimated travel time and distance

5. **Adjust as needed:**
   - You can change the transport mode and regenerate the map if desired

## Exporting to Google Maps

To use your planned route on your mobile device:

1. Click the "Export to Google Maps" button
2. Click the "Open in Google Maps" link
3. In Google Maps, use the "Send to your phone" feature to access the route on your mobile device
4. On your phone, you can then save or share the route as needed

## Tips and Tricks

- For best results, enter specific place names rather than general areas
- If a location isn't recognized, try adding more details (e.g., "Louvre Museum, Paris" instead of just "Louvre")
- The order of input doesn't matter; the app will optimize the route automatically
- Consider your mode of transport when planning – walking routes might be very different from driving routes!

## Troubleshooting

If you encounter issues:

- Ensure all location names are spelled correctly
- Check that you've selected the correct country and region
- Try refreshing the page and re-entering your locations
- If problems persist, try clearing your browser cache and cookies

## Contributing

This Trip Planner is an open-source project. If you're a developer and want to contribute:

1. Fork the repository
2. Create a new branch for your feature
3. Commit your changes
4. Push to your branch
5. Create a new Pull Request

I welcome contributions to improve and expand the functionality of the Trip Planner!

---

I hope you enjoy using the Trip Planner for your next adventure. Happy travels!
