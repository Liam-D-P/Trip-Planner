import os
import pandas as pd
import folium
import requests
import networkx as nx
import matplotlib.pyplot as plt
import webbrowser
import googlemaps
import streamlit as st
from streamlit_folium import folium_static
from folium import plugins as folium_plugins
from dotenv import load_dotenv
from geopy.distance import geodesic
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

load_dotenv()

API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
gmaps = googlemaps.Client(key=API_KEY)

@st.cache_data
def get_geocode(api_key, location):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": location, "key": api_key}
    return requests.get(url, params=params).json()

@st.cache_data
def process_locations(file, api_key):
    df = pd.read_excel(file)
    df['Address'] = df['Destination'].apply(lambda x: get_geocode(api_key, x + ", New York, NY")['results'][0]['formatted_address'] if get_geocode(api_key, x + ", New York, NY")['status'] == 'OK' else None)
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

def create_distance_graph(df, locations):
    G = nx.Graph()
    for i, origin in enumerate(locations):
        G.add_node(origin)
        for j, destination in enumerate(locations):
            if i != j:
                G.add_edge(origin, destination, weight=df.iloc[i, j])

    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, node_size=700, node_color='skyblue', font_size=8, font_weight='bold')
    labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=labels)
    plt.title("Distance Graph of Destinations")
    plt.axis('off')
    plt.tight_layout()
    return plt.gcf()

def main():
    st.title("NY Trip Planner")

    uploaded_file = st.file_uploader("Choose a file", type="xlsx")
    if uploaded_file is not None:
        df = process_locations(uploaded_file, API_KEY)
        st.success("File processed successfully!")

        locations = df['Destination'].tolist()
        addresses = df['Address'].tolist()
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

        transport_mode = st.selectbox("Select transport mode", ["driving", "walking", "bicycling", "transit"])

        if st.button("Generate Map"):
            if optimal_route:
                m = generate_map(optimal_route, locations, coordinates_dict, address_dict, mode=transport_mode)
                folium_static(m)
                st.success("Map generated successfully!")
            else:
                st.error("Failed to generate optimal route.")

        if st.button("Show Distance Graph"):
            fig = create_distance_graph(pd.DataFrame(distance_matrix, index=locations, columns=locations), locations)
            st.pyplot(fig)

if __name__ == "__main__":
    main()