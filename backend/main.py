from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
import psycopg2
import psycopg2.extras
from typing import Literal, List, Optional
 
app = FastAPI()

origins = ['http://localhost:5173', 'http://127.0.0.1:5173'] #allow frontend to connect
#ATTENTION: if backend is run as 127.0.0.1, CORS error arises! so use 0.0.0.0
app.add_middleware(
    CORSMiddleware,
    # allow_origins=origins,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


def get_db_connection():
    return psycopg2.connect(
        dbname='diffCellSig',
        user='postgres',
        password='postgres',
        host='localhost',
        port='5436'
    )

@app.get('/api/static_info')
def get_celltypes():
    """Return distinct cell types from the nodes table."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('SELECT DISTINCT celltype FROM nodes ORDER BY celltype DESC;')
    celltypes = [row[0] for row in cur.fetchall()]
    
    cur.execute('SELECT COUNT(*) FROM nodes;')
    total_nodes = cur.fetchone()[0]

    cur.execute('SELECT COUNT(*) FROM links;')
    total_links = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    return {'celltypes': celltypes, 'total_nodes': total_nodes, 'total_links': total_links}

@app.get('/api/filtered_data')
def get_filtered_network(
    sender: str = None,
    receiver: str = None,
    reverse_sig: bool = False,
    filter_intrascore: bool = False,
    filter_pv: bool = False,
    filter_inter: bool = False,
    min_intrascore: float = 0.5,
    max_intrascore: float = 1.0,
    pv_thresh: float = 0.05,
    focus_on_LR: bool = False,
    inter_dir: Literal['up', 'down'] = 'up'
):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    #get all potential nodes + filter by intrascore
    node_query = """
        SELECT * FROM nodes
        WHERE celltype IN (%s, %s)
    """
    params = [sender, receiver]

    if filter_intrascore:
        node_query += """
            AND (intrascore BETWEEN %s AND %s OR intrascore IS NULL)
        """
        params.extend([min_intrascore, max_intrascore])

    cur.execute(node_query, params)
    nodes = cur.fetchall()

    if not nodes:
        cur.close()
        conn.close()
        return {'nodes': [], 'links': []}

    valid_node_ids = [n['id'] for n in nodes]

    #filter links based on celltype+type
    if reverse_sig:#in case to include both directions (sender->receiver and receiver->sender)
        link_query = """
            SELECT l.*
            FROM links l
            JOIN nodes ns ON ns.id = l.source
            JOIN nodes nt ON nt.id = l.target
            WHERE l.source = ANY(%s)
                AND l.target = ANY(%s)
        """
        link_params =[valid_node_ids, valid_node_ids]
    else: #normal case: only sender->receiver
        link_query = """
            SELECT l.* 
            FROM links l
            JOIN nodes ns ON ns.id = l.source
            JOIN nodes nt ON nt.id = l.target
            WHERE l.source = ANY(%s)
                AND l.target = ANY(%s)
                AND (
                    (l.type = 'TFL' AND ns.celltype = %s AND nt.celltype = %s)
                    OR
                    (l.type = 'LR' AND ns.celltype = %s AND nt.celltype = %s)
                    OR 
                    (l.type = 'RTF' AND ns.celltype = %s AND nt.celltype = %s)
                    )
        """
        link_params = [valid_node_ids, valid_node_ids, 
                    sender, sender, #TFL layer
                    sender, receiver, #LR layer
                    receiver, receiver  #RTF layer
                    ]
    
    if filter_pv:
        link_query += " AND (l.significance < %s OR l.significance IS NULL)"
        link_params.append(pv_thresh)

    if filter_inter:
        if inter_dir == 'up':
            link_query += " AND ((l.type = 'LR' AND l.weight > 0) OR l.type != 'LR')"
        else:
            link_query += " AND ((l.type = 'LR' AND l.weight < 0) OR l.type != 'LR')"

    cur.execute(link_query, link_params)
    links = cur.fetchall()

    #remove nodes that do NOT appear in any link
    if links:
        connected_ids = {l['source'] for l in links} | {l['target'] for l in links}
        filtered_nodes = [n for n in nodes if n['id'] in connected_ids]
    else:
        filtered_nodes = []

    # as last step, keep only LR nodes involved in diff CCC and their neighbors 
    if focus_on_LR and filtered_nodes:
        diff_lr_ids = [l['source'] for l in links if l['type'] == 'LR'] + [l['target'] for l in links if l['type'] == 'LR']
        TF_neighbors = [l['source'] for l in links if l['type'] == 'TFL' and l['target'] in diff_lr_ids] + \
                        [l['target'] for l in links if l['type'] == 'RTF' and l['source'] in diff_lr_ids]
        focus_ids = set(diff_lr_ids + TF_neighbors)
        filtered_nodes = [n for n in filtered_nodes if n['id'] in focus_ids]
        links = [l for l in links if l['source'] in focus_ids and l['target'] in focus_ids]

    stats = {
        'nNodes': len(filtered_nodes),
        'nLigands': 0,
        'nReceptors': 0,
        'nTFs': 0,
        'nLinks': len(links),
        'nLRLinks': 0,
        'nTFLLinks': 0,
        'nRTFLinks': 0,
        'unexpectedNodes': 0,
        'unexpectedLinks': 0
    }
    for n in filtered_nodes:
        if n['moltype'] == "ligand":
            stats['nLigands'] += 1
        elif n['moltype'] == "receptor":
            stats['nReceptors'] += 1
        elif n['moltype'] == "TF":
            stats['nTFs'] += 1
        else:
            stats['unexpectedNodes'] += 1
    for l in links:
        if l['type'] == "LR":
            stats['nLRLinks'] += 1
        elif l['type'] == "TFL":
            stats['nTFLLinks'] += 1
        elif l['type'] == "RTF":
            stats['nRTFLinks'] += 1
        else:
            stats['unexpectedLinks'] += 1

    cur.close()
    conn.close()

    return {
        'nodes': filtered_nodes,
        'links': links,
        'stats': stats
    }

@app.get('/api/molecules_names_list')
def get_molecules_names_list():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT name FROM nodes ORDER BY name ASC;')
    names = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    #save this just temporarily to a file for Stefan
    # with open("molecules.txt", "w") as outfile:
    #     outfile.write("\n".join(names))
    # TO BE REMOVED
    return {'molecules': names}


# @app.get('/api/filtered_data')
# def get_filtered_network(
#     sender: str = None,
#     receiver: str = None,
#     filter_intrascore: bool = False,
#     filter_pv: bool = False,
#     filter_inter: bool = False,
#     min_intrascore: float = 0.0,
#     max_intrascore: float = 1.0,
#     pv_thresh: float = 0.05,
#     inter_dir: Literal['up', 'down'] = 'up'
# ):
#     conn = get_db_connection()
#     cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

#     query_nodes = "SELECT * FROM nodes WHERE (celltype = %s OR celltype = %s) "
#     params = [sender, receiver]

#     if filter_intrascore:
#         query_nodes += "AND ( (intrascore BETWEEN %s AND %s) OR intrascore IS NULL ) "
#         params.extend([min_intrascore, max_intrascore])
#     query_nodes += ";"

#     cur.execute(query_nodes, params)
#     nodes = cur.fetchall()
#     valid_ids = [n['id'] for n in nodes]

#     query_links = "SELECT * FROM links WHERE 1=1 "
#     params = []
#     if valid_ids:
#         query_links += "AND (source = ANY(%s) AND target = ANY(%s)) "
#         params.extend([valid_ids, valid_ids])
#     if filter_pv:
#         query_links += "AND ( (significance < %s) OR significance IS NULL ) "
#         params.append(pv_thresh)
#     if filter_inter:
#         if inter_dir == 'up':
#             query_links += 'AND ( (weight > 0) OR weight IS NULL ) '
#         else:
#             query_links += 'AND ( (weight < 0) OR weight IS NULL ) '
#     query_links += ';'
#     cur.execute(query_links, params)
#     links = cur.fetchall()

#     cur.close()
#     conn.close()
#     return {'nodes': nodes, 'links': links}


# @app.get('/api/stats')
# def get_stats(filtered_data_url: str):
#     """ Return basic stats about the database """
#     conn = get_db_connection(filtered_data_url)
#     cur = conn.cursor()
#     stats = {}

#     cur.execute('SELECT COUNT(*) FROM nodes;')
#     stats['nNodes'] = cur.fetchone()[0]
#     cur.execute("SELECT COUNT(*) FROM nodes WHERE moltype = 'ligand';")
#     stats['nLigands'] = cur.fetchone()[0]
#     cur.execute("SELECT COUNT(*) FROM nodes WHERE moltype = 'receptor';")
#     stats['nReceptors'] = cur.fetchone()[0]
#     cur.execute("SELECT COUNT(*) FROM nodes WHERE moltype = 'TF';")
#     stats['nTFs'] = cur.fetchone()[0]
#     cur.execute('SELECT COUNT(*) FROM links;')
#     stats['nLinks'] = cur.fetchone()[0]
#     cur.execute('SELECT COUNT(*) FROM links;')
#     stats['nLinks'] = cur.fetchone()[0]
    
#     cur.execute("SELECT COUNT(*) FROM links WHERE type = 'LR';")
#     stats['nLRLinks'] = cur.fetchone()[0]
#     cur.execute("SELECT COUNT(*) FROM links WHERE type = 'TFL';")
#     stats['nTFLLinks'] = cur.fetchone()[0]
#     cur.execute("SELECT COUNT(*) FROM links WHERE type = 'RTF';")
#     stats['nRTFLinks'] = cur.fetchone()[0]
    
#     cur.close()
#     conn.close()

#     return stats


# @app.get('/api/celltypes/{celltype}')
# def get_nodes_by_celltype(celltype: str):
#     """ return rows from nodes table matching selected cell type """
#     conn = get_db_connection()
#     cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
#     cur.execute(f"SELECT * FROM nodes WHERE celltype = '{celltype}';")
#     rows = cur.fetchall()
#     cur.close()
#     conn.close()

#     if not rows:
#         raise HTTPException(status_code=404, detail=f"No entries found for cell type {celltype}")

#     #convert to list of dicts for JSON serialization
#     result = [dict(row) for row in rows]
#     return {'celltype': celltype, 'nodes': result}


# Example endpoint to fetch data from the database
# @app.get('/api/data')
# def get_nodes():
#     conn = get_db_connection()
#     cur = conn.cursor()
#     cur.execute('SELECT nodes FROM information_schema.tables WHERE table_schema="public";')
#     tables = cur.fetchall()
#     cur.close()
#     conn.close()
#     return {'tables': [t[0] for t in tables]}
