import pandas as pd
import geopandas as gpd
import folium
import streamlit as st
from streamlit_folium import folium_static, st_folium
from geographiclib.geodesic import Geodesic
from shapely.geometry import Polygon
from pathlib import Path

from params import *
from data import get_data_with_cache

def main():
    # Config for website
    st.set_page_config(
        page_title= 'Poverty Mapper',
        page_icon="🌍",
        layout = "wide",
        initial_sidebar_state="expanded")

    with st.sidebar:
        st.header('Select region')
        country = st.selectbox(label = 'Country', label_visibility='collapsed',options=('France', 'Italy', 'USA','New Zealand'))
        region = st.radio(label='Region', options=('REG01', 'REG02', 'REG03', 'REG04', 'REG05', 'REG06', 'REG07'))

    st.title('Poverty Mapper')

    query = f"""
        SELECT {",".join(COLUMN_NAMES_RAW)}
        FROM {GCP_PROJECT}.{BQ_DATASET}.DHS_CLUSTERS
        """
    df_cache_path = Path(LOCAL_DATA_PATH).joinpath("DHS_CLUSTERS.csv")
    df = get_data_with_cache(query=query,
                             gcp_project=GCP_PROJECT,
                             cache_path=df_cache_path,
                             data_has_header=True)

    df = df[df['year'] == 2015]
    # df = df[df['country'] == 'angola']
    # df = df[df['GID_1'] == 'AGO.1']
    # st.map(df)

    geod = Geodesic.WGS84
    tile_size = 67200 #in meters

    df['lat_max'] = df.apply(lambda x: geod.Direct(x.lat, x.lon, 0, tile_size/2)['lat2'], axis=1)
    df['lon_max'] = df.apply(lambda x: geod.Direct(x.lat, x.lon, 90, tile_size/2)['lon2'], axis=1)
    df['lat_min'] = df.apply(lambda x: geod.Direct(x.lat, x.lon, 180, tile_size/2)['lat2'], axis=1)
    df['lon_min'] = df.apply(lambda x: geod.Direct(x.lat, x.lon, 270, tile_size/2)['lon2'], axis=1)
    df['geometry'] = df.apply(lambda x: Polygon(zip([x.lon_min, x.lon_max, x.lon_max, x.lon_min],
                                                    [x.lat_min, x.lat_min, x.lat_max, x.lat_max])), axis=1)

    gdf = gpd.GeoDataFrame(df)
    m = folium.Map(location=[gdf.lat.mean(), gdf.lon.mean()], zoom_start=3)

    cm = folium.LinearColormap(["purple", "white", "orange"], caption="Wealthpooled",
                               vmin=min(gdf['wealthpooled']), vmax=max(gdf['wealthpooled']))

    style_function = lambda feature: {
        "fillColor": cm(feature["properties"]["wealthpooled"]),
        "fillOpacity": 0.8,
        "weight": 0.8,
        "color": cm(feature["properties"]["wealthpooled"]),
    }

    #Add the colormap as a legend
    cm.add_to(m)

    folium.GeoJson(
        gdf.__geo_interface__,
        style_function=style_function,
        tooltip=folium.features.GeoJsonTooltip(["wealthpooled"])
    ).add_to(m)

    st_data = folium_static(m, width = 900)
    # st_data = st_folium(m, width = 1500)

if __name__ == '__main__':
    main()
