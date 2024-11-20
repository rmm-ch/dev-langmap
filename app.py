from dash import Dash, html, dcc, callback, Output, Input, dash_table
import plotly.express as px
import pandas as pd
import numpy as np
import json

disp = 'lang'
disp = 'dow'
filter_out_missing = False
#filter_out_missing = True
missing_sentinel = 'missing data'
#missing_sentinel = 'other'

def load_data(filter_out_missing:bool=False):
    df1 = pd.read_csv('data.csv')
    df = df1[['country', 'data.people.population.total', 'data.people.languages.language']]

    default = [{'name':'null'},]
    df['langdict'] = df['data.people.languages.language'].apply(lambda x: default[:] if type(x) == float else json.loads(x))

    # extract the first language from the langdict list. it is a dict, so we need to extract the 'name' key.
    df['language'] = df['langdict'].apply(lambda x: x[0]['name'])


    # load data from lang2dow.csv
    dow_cats = pd.read_csv('lang2dow.csv')
    # strip the quotes and spaces from the language column
    dow_cats['language'] = dow_cats['language'].apply(lambda x: x.strip('\' '))

    # merge the dataframes on the language column, only taking the dow_category column
    df = pd.merge(df, dow_cats[['language', 'dow_category']], on='language', how='left')

    # drop the row for country == World
    df = df[df['country'] != 'World']


    if filter_out_missing:
        # convert missing and blank vales to NaN so they don't show up in the map
        df['dow_category'] = df['dow_category'].apply(lambda x: np.nan if x == ' '  else x)
    else:
        df['dow_category'] = df['dow_category'].apply(lambda x: missing_sentinel if x == ' '  else x)
        
    # make some aggs to have a continuous scale for color choice
    pop_by_dow_raw = df.groupby('dow_category')['data.people.population.total'].sum() / df['data.people.population.total'].sum()*100
    # make a categorical variable based on the rank of the population percentage
    pop_by_dow = pop_by_dow_raw.sort_values(ascending=False)
    pop_by_dow = pop_by_dow.reset_index()
    pop_by_dow['rank'] = pop_by_dow.index
    pop_by_dow = pop_by_dow.set_index('dow_category')
    
    
    # put the data back into the dataframe
    #df['category_pop_pct'] = df['dow_category'].apply(lambda x: pop_by_dow[x] if x in pop_by_dow else -1)
    df['category_idx'] =  df['dow_category'].apply(lambda x: pop_by_dow.loc[x, 'rank'] if x in pop_by_dow.index else -1)

    # convert 'category_pop' to categorical, setting the mapping to rank:dow_category
    rank_to_dow = pop_by_dow.reset_index().set_index('rank')['dow_category'].to_dict()
    dow_to_rank = {v:k for k, v in rank_to_dow.items()}

    if 0:
        dow_to_rank = {v:k for k, v in rank_to_dow.items()}
        if missing_sentinel in dow_to_rank:
            new_rank = max(rank_to_dow.keys()) + 1
            old_rank = dow_to_rank[missing_sentinel]
            rank_to_dow[new_rank] = missing_sentinel
            rank_to_dow.pop(old_rank)
            print(f"other was rank {old_rank}, now is {new_rank}. for other.")
        
        print(rank_to_dow)
        
    # add the numerical rank to the text so we can see the choices.
    rank_to_dow = {k: f"{v} (g{k})" for k, v in rank_to_dow.items()}
    #print(rank_to_dow)

    #df['category_idx'] = df['category_pop'].apply(lambda x: dow_to_rank.get(x, None))
    #print(df.head())

    df['category_pop'] = df['category_idx'].apply(lambda x: rank_to_dow.get(x, None))
    #df['category_pop'] = df['category_pop'].apply(lambda x: dow_to_rank.get(x, None))
    #df['category_pop'] = df['category_pop'].apply(lambda x: rank_to_dow.get(x, 'other'))
    # define the category_pop as a categorical variable, and set the codes to the rank
    df['category_pop'] = pd.Categorical(df['category_pop'], categories=rank_to_dow.values(), ordered=True)
    df['category_idx2'] = df['category_pop'].cat.codes
    #               
    
    #df['category_pop'] = df['category_pop'].astype('category')
    #df['category_idx'] = df['category_pop'].cat.codes

    
    print("==="*15)
    print(dow_to_rank)
    print("==="*15, " categories")
    print(df['category_pop'].cat.categories)
    print("==="*15, " codes")
    print(df['category_pop'].cat.codes)
    print("==="*15 )
    print(df.head())
    
    
    
    

    
    return df


def build_filter_df(df:pd.DataFrame,) -> pd.DataFrame:
    pops = df.groupby('dow_category')['population'].sum()
    pops = pops.sort_values(ascending=False).reset_index()
    pops['rank'] = pops.index
    rank_by_cat = pops.set_index('dow_category')
    return rank_by_cat


    


#df = load_data(filter_out_missing)

def get_default_df() -> pd.DataFrame:
    df = load_data(filter_out_missing) # using a global boolean :(
    # rename long population col
    df = df.rename(columns={'data.people.population.total':'population'})
    sel_cols = ['country', 'language', 'dow_category', 'category_pop', 'population', 'category_idx', 'category_idx2']
    
    return df[sel_cols]

palletes_qual = [p for p in dir(px.colors.qualitative) if not p.startswith('_')]

app = Dash(__name__)
server = app.server

app.layout = [
    html.H1(children='Where are days of the week derived from?', style={'textAlign':'center'}),
    dcc.Dropdown(palletes_qual, 'T10',  id='dropdown-selection'),
    #dcc.Dropdown(df.country.unique(), 'Canada', id='dropdown-selection'),
    html.Button('Refresh data', id='refresh-button'),
    dcc.Store(id='dataframe'),
    dcc.Graph(id='graph-content'),
    html.Pre(id='click-data', style={'border': 'thin lightgrey solid', 'overflowX': 'scroll'}),
    html.Div(id='table-container', style={'width':'80%', 'margin-left':'1%', 'align':'left'},
             children=[ dash_table.DataTable(
                 id='table', data=get_default_df().to_dict('records'),
                 #columns=[{'name': i, 'id': i} for i in get_default_df().columns if i != 'category_idx'],
                 sort_action='native', row_selectable='single',
             ),
                    
    ]),
]


#@callback(
#    Output('click-data', 'children'),
#    Input('graph-content', 'clickData'))
#def display_click_data(clickData):
#    # this allows us to see the info from the location (clickData)
#    return json.dumps(clickData, indent=2)

@callback(
    Output('click-data', 'children'),
    Input('graph-content', 'restyleData'))
def display_click_data(restyleData):
    # this allows us to see the info from the selected group, great.
    return json.dumps(restyleData, indent=2)



@callback(
    Output('dataframe', 'data'),
    Input('refresh-button', 'n_clicks')
)
def update_data(n_clicks):
    print(f"[I] refresh button clicked {n_clicks} times.")
    df = load_data(filter_out_missing) # using a global boolean :(
    return df.to_json(date_format='iso', orient='split')


@callback(
    Output('table', 'data'),
    Input('graph-content', 'restyleData'),
)
def update_table_filtered(restyleData):
    df = get_default_df()
    rank_by_cat = build_filter_df(df)
    cat_by_rank = rank_by_cat.reset_index().set_index('rank')['dow_category'].to_dict()
    
    # now we need to filter the dataframe based on the selected category.
    # the data in restlyeData is a list of dicts, we need to find the one with visible: [ list of booleans]
    if not restyleData:
        return df.to_dict('records')
    
    for chunk in restyleData:
        if 'visible' in chunk:
            visible = chunk['visible']
            break
    else:
        visible = [True] * len(cat_by_rank)
    # there is another edge case, where the first selection is not doubleclick, but a de-selection. then we just get one
    # element that is 'legendonly'. maybe easier to just keep track of our own state?
    
    sel_grps = []
    for i, cat in enumerate(visible):
        if cat == True:
            sel_grps.append(i)

    # build a query string to filter the dataframe, from the numbers in sel_grps, use as indices into the dict cat_by_rank
    # let's build a different query method.
    #category_idx
    print(sel_grps)
    if sel_grps:
        df = df[df.category_idx.isin(sel_grps)]
    
    #query = ' | '.join([f"dow_category == '{cat_by_rank[grp]}'" for grp in sel_grps])
    #print(f"[I] query: {query}")
    
    #if query:
    #    df = df.query(query)
    # if there was nothing in restlyedata, we don't filter.
            
    
    return df.to_dict('records')


@callback(
    Output('graph-content', 'figure'),
    Input('dropdown-selection', 'value'),
    Input('dataframe', 'data')
)
def update_graph(value, data):
    #dff = df[df.country==value]
    #return px.line(dff, x='year', y='pop')
    df = pd.read_json(data, orient='split')
    

    if disp == 'lang':
        pass
    elif disp == 'dow':
        fig = px.choropleth(
            df.sort_values(by='category_idx'),
            #geojson=counties_50m,
            locations='country',  # Column with country names
            locationmode='country names',  # Use country names for location
            #color='dow_category',
            color='category_pop',
            #labels='dow_category',
            #map_style="carto-positron",
            hover_name='dow_category',
            #color_continuous_scale='viridis',  # You can change this color scale
            color_discrete_sequence=getattr(px.colors.qualitative, value),
            #title='Country Categorization Map',
            custom_data=['country', 'language', 'dow_category'        ],
            
        )
        fig.update_traces(
            hovertemplate =
                    "<b>%{customdata[0]}</b><br><br>" +
                    "<i>%{customdata[1]}</i><br>" +
                    "<i>%{customdata[2]}</i><br>" +
                    "<extra></extra>",
            #mode='markers',
            #marker={'sizemode':'area',
            #        'sizeref':10},
        )
        fig.update_geos(projection_type="natural earth",
                        resolution=50,
                        lataxis_showgrid=True,
                        showsubunits=True, subunitcolor="Blue"
                        )



    if 1:
        fig.update_layout(
            geo_scope='world',  # Set the map scope
            #geo_scope='europe',  
            width=1200,  # Adjust width
            height=800   # Adjust height
        )

        #fig.write_html('choropleth_map.html')
    return fig

if __name__ == '__main__':
    app.run(debug=True)
