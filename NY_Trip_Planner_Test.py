import os
import pandas as pd
import folium
import requests
import googlemaps
import streamlit as st
from streamlit_folium import folium_static
import webbrowser
from dotenv import load_dotenv
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from urllib.parse import quote

load_dotenv()
API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

secrets_path = os.path.join(os.path.expanduser('~'), '.streamlit', 'secrets.toml')
os.makedirs(os.path.dirname(secrets_path), exist_ok=True)
with open(secrets_path, 'w') as f:
    f.write(f'GOOGLE_MAPS_API_KEY = "{API_KEY}"')

API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
gmaps = googlemaps.Client(key=API_KEY)

@st.cache_data
def get_geocode(api_key, location):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": location, "key": api_key}
    return requests.get(url, params=params).json()

@st.cache_data
def process_locations(file, api_key, country, region):
    df = pd.read_excel(file)
    df['Address'] = df['Destination'].apply(lambda x: get_geocode(api_key, f"{x}, {region}, {country}")['results'][0]['formatted_address'] if get_geocode(api_key, f"{x}, {region}, {country}")['status'] == 'OK' else None)
    return df

@st.cache_data
def get_distance_matrix(api_key, origins, destinations):
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {"origins": "|".join(origins), "destinations": "|".join(destinations), "key": api_key}
    return requests.get(url, params=params).json()

@st.cache_data
def fetch_and_save_distance_matrix(api_key, addresses):
    distance_matrix_data = get_distance_matrix(api_key, addresses, addresses)
    
    num_locations = len(addresses)
    distance_matrix = [[distance_matrix_data['rows'][i]['elements'][j]['distance']['value'] 
                        if distance_matrix_data['rows'][i]['elements'][j]['status'] == 'OK' 
                        else None 
                        for j in range(num_locations)] 
                       for i in range(num_locations)]
    
    return distance_matrix

def create_data_model(distance_matrix, address_dict):
    return {'distance_matrix': distance_matrix, 'num_vehicles': 1, 'depot': 0, 'addresses': address_dict}

def solve_tsp(data):
    manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']), data['num_vehicles'], data['depot'])
    routing = pywrapcp.RoutingModel(manager)
    
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]
    
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    solution = routing.SolveWithParameters(search_parameters)
    
    if not solution:
        return None
    
    index = routing.Start(0)
    plan_output = []
    while not routing.IsEnd(index):
        plan_output.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))
    plan_output.append(manager.IndexToNode(index))
    return plan_output

def generate_map(optimal_route, locations, coordinates_dict, address_dict, mode='driving'):
    mid_point = coordinates_dict[locations[optimal_route[len(optimal_route)//2]]]
    m = folium.Map(location=mid_point, zoom_start=12)

    for idx in range(len(optimal_route) - 1):
        start, end = locations[optimal_route[idx]], locations[optimal_route[idx + 1]]
        start_coords, end_coords = coordinates_dict[start], coordinates_dict[end]
        
        directions_result = gmaps.directions(start_coords, end_coords, mode=mode)
        
        if directions_result:
            route = directions_result[0]['overview_polyline']['points']
            decoded_route = googlemaps.convert.decode_polyline(route)
            formatted_route = [(point['lat'], point['lng']) for point in decoded_route]
            
            polyline = folium.PolyLine(
                locations=formatted_route,
                color='blue',
                weight=5,
                opacity=0.8
            ).add_to(m)

            folium.plugins.PolyLineTextPath(
                polyline=polyline,
                text=f"Leg {idx + 1}",
                offset=8,
                repeat=False,
                attributes={"font-weight": "bold", "font-size": "14", "fill": "black"}
            ).add_to(m)

        for point, name, num in [(start_coords, start, idx + 1), (end_coords, end, idx + 2)]:
            folium.Marker(
                location=point,
                icon=folium.DivIcon(html=f'''
                    <div style="font-size: 12pt; color: black; background: linear-gradient(135deg, #72EDF2 10%, #5151E5 100%);
                        border-radius: 8px; padding: 5px; width: 140px; word-wrap: break-word; text-align: center;
                        box-shadow: 2px 2px 12px rgba(0, 0, 0, 0.2);">
                        {num}. {name}
                    </div>
                ''')
            ).add_to(m)

        if directions_result:
            travel_time = directions_result[0]['legs'][0]['duration']['text']
            distance = directions_result[0]['legs'][0]['distance']['text']
            mid_point = formatted_route[len(formatted_route)//2]
            folium.Marker(
                location=mid_point,
                icon=folium.DivIcon(html=f'''
                    <div style="font-size: 10pt; color: black; background: rgba(255, 255, 255, 0.8);
                        border: 1px solid black; border-radius: 5px; padding: 5px; width: 140px; 
                        word-wrap: break-word; text-align: center;">
                        Time: {travel_time}<br>Distance: {distance}
                    </div>
                ''')
            ).add_to(m)

    sw = min(coord[0] for coord in coordinates_dict.values()), min(coord[1] for coord in coordinates_dict.values())
    ne = max(coord[0] for coord in coordinates_dict.values()), max(coord[1] for coord in coordinates_dict.values())
    m.fit_bounds([sw, ne])

    return m

def generate_google_maps_url(locations, optimal_route, transport_mode):
    base_url = "https://www.google.com/maps/dir/?api=1"
    
    # Use the optimal route to order the locations
    ordered_locations = [locations[i] for i in optimal_route]
    
    # Set origin, destination, and waypoints
    origin = quote(ordered_locations[0])
    destination = quote(ordered_locations[-1])
    waypoints = "|".join(quote(loc) for loc in ordered_locations[1:-1])
    
    # Construct the URL
    url = f"{base_url}&origin={origin}&destination={destination}&waypoints={waypoints}&travelmode={transport_mode}"
    
    return url


def get_transport_mode_value(mode):
    mode_map = {
        "driving": "0",
        "walking": "2",
        "bicycling": "1",
        "transit": "3"
    }
    return mode_map.get(mode, "0") 

def main():
    st.title(':blue[Trip Planner] :airplane:')
    st.subheader("Plan your trip with ease! Just add a list of places you want to visit and the application will generate the optimal route for you.", divider='rainbow')
    st.markdown("This maximum amount of locations you can enter is 10.")
    country = st.selectbox("Select a country", ["United Kingdom", "United States"])
    region = st.text_input("Enter a region or state within the selected country")
    city = st.text_input("Enter a city")

    if 'locations' not in st.session_state:
        st.session_state.locations = []

    locations = []
    for i in range(10):
        location = st.text_input(f"Enter location {i+1}", key=f"location_{i}")
        if location:
            locations.append(location)

    if 'map_generated' not in st.session_state:
        st.session_state.map_generated = False

    if locations != st.session_state.locations:
        st.session_state.locations = locations
        st.session_state.map_generated = False

    generate_map_button = st.button("Generate Map")

    if generate_map_button or st.session_state.map_generated:
        if locations:
            transport_mode = st.selectbox("Select transport mode", ["driving", "walking", "bicycling", "transit"])

            if not st.session_state.map_generated or 'transport_mode' not in st.session_state or st.session_state.transport_mode != transport_mode:
                st.session_state.transport_mode = transport_mode

                addresses = [f"{loc}, {city}, {region}, {country}" for loc in locations]
                address_dict = dict(zip(locations, addresses))

                distance_matrix = fetch_and_save_distance_matrix(API_KEY, addresses)
                
                coordinates_dict = {}
                for loc, addr in address_dict.items():
                    result = gmaps.geocode(addr)
                    if result:
                        location = result[0]['geometry']['location']
                        coordinates_dict[loc] = (location['lat'], location['lng'])
                    else:
                        coordinates_dict[loc] = (None, None)

                data = create_data_model(distance_matrix, address_dict)
                optimal_route = solve_tsp(data)

                if optimal_route:
                    st.success("Map generated successfully!")
                    m = generate_map(optimal_route, locations, coordinates_dict, address_dict, mode=transport_mode)
                    st.session_state.map = m
                    st.session_state.map_generated = True
                    st.session_state.optimal_route = optimal_route  # Store optimal_route in session state
                    folium_static(m)
                else:
                    st.error("Failed to generate optimal route. Please check your input locations and try again.")
            else:
                # If the map was already generated and transport mode hasn't changed, just display the existing map
                folium_static(st.session_state.map)

            # Move this outside of the if-else block
            if st.session_state.get('map_generated', False):
                if 'show_maps_info' not in st.session_state:
                    st.session_state.show_maps_info = False

                if st.button("Export to Google Maps"):
                    st.session_state.show_maps_info = True

                if st.session_state.show_maps_info:
                    if 'optimal_route' in st.session_state and st.session_state.locations:
                        google_maps_url = generate_google_maps_url(st.session_state.locations, st.session_state.optimal_route, st.session_state.transport_mode)
                        st.markdown(f"[Open in Google Maps]({google_maps_url})")
                
                        st.info("""
                        After opening your route in Google Maps, you can use these features:

                        1. Send to Phone: 
                        - On desktop, look for the "Send to your phone" button in the left sidebar.
                        - You'll receive a notification on your phone with the route.

                        2. Save the Route (on mobile):
                        - Open the route on your Google Maps mobile app.
                        - Tap the "Save" button at the bottom of the screen.
                        - Choose a list to save to or create a new one.

                        3. Share the Route:
                        - Tap the "Share" button in Google Maps.
                        - Choose how you want to share (e.g., via message, email, etc.)

                        These features allow you to easily access your planned route on your mobile device and save it for future reference.
                        """)
                    else:
                        st.error("Please generate a route first.")
        else:
            st.error("Please enter at least one location.")

if __name__ == "__main__":
    main()
