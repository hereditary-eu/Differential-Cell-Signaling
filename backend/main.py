from fastapi import FastAPI
from fastapi import Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras
from typing import Literal
import statistics
import networkx as nx
from collections import Counter

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
        dbname='diffcellsig',
        user='postgres',
        password='postgres',
        host='localhost',
        port='5436'
    )

@app.get('/api/neighborhood')
def get_neighborhood_data(node_id: str, comparison: str, sender: str, receiver: str, max_depth: int = 4):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT *
        FROM nodes
        WHERE id = %s
    """, (node_id,))
    rootnode = cur.fetchone()
    if not rootnode:
        cur.close()
        conn.close()
        return {"rootnode": None, "neighbors": [], "links": []}
    #filter nodes subset
    cur.execute("""
        SELECT id
        FROM nodes
        WHERE comparison = %s
        AND celltype IN (%s, %s)
    """, (comparison, sender, receiver))
    valid_node_ids = [row["id"] for row in cur.fetchall()]
    
    cur.execute("""
        WITH RECURSIVE graph AS (
            -- Start from root node
            SELECT id, 0 AS depth
            FROM nodes
            WHERE id = %s

            UNION ALL

            -- Expand neighbors only if they are in the valid subset
            SELECT
                CASE
                    WHEN l.source = g.id THEN l.target
                    ELSE l.source
                END AS id,
                g.depth + 1
            FROM graph g
            JOIN links l
                ON (l.source = g.id OR l.target = g.id)
            WHERE g.depth < %s
              AND (CASE WHEN l.source = g.id THEN l.target ELSE l.source END) = ANY(%s)
        )
        SELECT DISTINCT id
        FROM graph;
    """, (node_id, max_depth, valid_node_ids))

    node_ids = [row["id"] for row in cur.fetchall()]
    if not node_ids:
        cur.close()
        conn.close()
        return {"rootnode": None, "neighbors": [], "links": []}

    #get all nodes in neighborhood
    cur.execute("""
        SELECT *
        FROM nodes
        WHERE id = ANY(%s)
    """, (node_ids,))
    nodes = cur.fetchall()
    #get all links between these nodes
    cur.execute("""
        SELECT *
        FROM links
        WHERE source = ANY(%s)
        AND target = ANY(%s)
        AND comparison = %s
    """, (node_ids, node_ids, comparison))
    links = cur.fetchall()

    cur.close()
    conn.close()
    return {'rootnode': rootnode,'neighbors': nodes, 'links': links}

# benedikt if u see this, it's just temporary!!!! :) i'll switch to puppygraph. es tut mir leid
def normalize_cycle(cycle):
    """Normalize a cycle to remove rotational duplicates."""
    min_index = cycle.index(min(cycle))
    return tuple(cycle[min_index:] + cycle[:min_index])

@app.get("/api/cycles")
def find_cycles(comparison: str):
    print('starting cycles computation...')
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get edges with node info (celltype)
    cur.execute("""
        SELECT l.source, l.target, l.type, 
               ns.celltype AS source_celltype, 
               nt.celltype AS target_celltype
        FROM links l
        JOIN nodes ns ON ns.id = l.source
        JOIN nodes nt ON nt.id = l.target
        WHERE l.comparison = %s
    """, (comparison,))
    edges = cur.fetchall()
    cur.close()
    conn.close()
    print(f"Fetched {len(edges)} edges for cycle detection.")
    if not edges:
        return {"cycles": []}
    
    #need to have all three layers involved to find a cycle
    found_e_types: set = set(e['type'] for e in edges)
    if len(found_e_types) < 3:
        return {"cycles": []}

    G = nx.DiGraph()
    node_celltype = {}
    for e in edges:
        G.add_edge(e['source'], e['target'], type=e['type'])
        node_celltype[e['source']] = e['source_celltype']
        node_celltype[e['target']] = e['target_celltype']
        # Make LR edges undirected
        if e['type'] == 'LR':
            G.add_edge(e['target'], e['source'], type='LR')

    # Find cycles using networkx
    raw_cycles = list(nx.simple_cycles(G))

    # Remove rotational duplicates 
    unique_cycles_set = set()
    filtered_cycles = []
    for cycle in raw_cycles:
        normalized = normalize_cycle(cycle)
        if normalized not in unique_cycles_set:
            unique_cycles_set.add(normalized)
            # Add celltype info for display and frontend
            cycle_nodes = [
                {"id": node, "celltype": node_celltype[node]} 
                for node in cycle
            ]
            display_string = " - ".join(
                [f"{n['id']} ({n['celltype']})" for n in cycle_nodes] + 
                [f"{cycle_nodes[0]['id']} ({cycle_nodes[0]['celltype']})"]
            )
            filtered_cycles.append({
                "id": len(filtered_cycles) + 1,
                "length": len(cycle),
                "nodes": cycle_nodes,
                "display": display_string
            })
    print(filtered_cycles)
    print('finished cycles computation!')
    return {"cycles": filtered_cycles}

def precompute(comparison: str):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute('SELECT id FROM nodes WHERE comparison = %s;', (comparison,))
    nodes = cur.fetchall()
    cur.execute(
        'SELECT source, target, type FROM links WHERE (significance < 0.05 OR significance IS NULL) AND comparison = %s;',
        (comparison,)
    )
    links = cur.fetchall()
    if links:
        connected_ids = {l['source'] for l in links} | {l['target'] for l in links}
        nodes = [n for n in nodes if n['id'] in connected_ids]
    else:
        nodes = []
    
    G = nx.DiGraph()
    G.add_nodes_from(n['id'] for n in nodes)
    G.add_edges_from((l['source'], l['target']) for l in links)
    G.add_edges_from((l['target'], l['source']) for l in links if l['type'] == 'LR') #make LRs undirected
    # k=min(n,200) approximation for large graphs
    n_nodes = G.number_of_nodes()
    k = min(n_nodes, 300) if n_nodes > 300 else None
    betweenness = nx.betweenness_centrality(G, k=k, normalized=True)
    values = list(betweenness.values())
    if len(values) >= 4:
        q1 = statistics.quantiles(values, n=4)[0]
        q3 = statistics.quantiles(values, n=4)[2]
        b_threshold = q3 + 1.5 * (q3 - q1)
    else:
        b_threshold = float('inf')

    pagerank = nx.pagerank(G, max_iter=100)
    values = list(pagerank.values())
    if len(values) >= 4:
        q1 = statistics.quantiles(values, n=4)[0]
        q3 = statistics.quantiles(values, n=4)[2]
        p_threshold = q3 + 1.5 * (q3 - q1)
    else:
        p_threshold = float('inf')
    
    cur2 = conn.cursor()
    for node_id, b in betweenness.items():
        p = pagerank.get(node_id, 0.0)
        cur2.execute(
            """UPDATE nodes SET betweenness = %s, pagerank = %s, is_outlier_b = %s, is_outlier_p = %s
               WHERE id = %s""",
            (b, p, bool(b > b_threshold), bool(p > p_threshold), node_id)
        )
    conn.commit()
    cur2.close()
    cur.close()
    conn.close()
    
@app.get('/api/centrality_status')
def centrality_status(comparison: str):
    """Check if centrality has already been computed for this comparison."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        ALTER TABLE nodes
        ADD COLUMN IF NOT EXISTS betweenness FLOAT,
        ADD COLUMN IF NOT EXISTS pagerank FLOAT,
        ADD COLUMN IF NOT EXISTS is_outlier_b BOOLEAN,
        ADD COLUMN IF NOT EXISTS is_outlier_p BOOLEAN;
    """)
    conn.commit()
    cur.execute(
        "SELECT EXISTS(SELECT 1 FROM nodes WHERE comparison = %s AND betweenness IS NOT NULL);",
        (comparison,)
    )
    computed = cur.fetchone()[0]
    cur.close()
    conn.close()
    return {'computed': computed}

@app.post('/api/precompute')
def precompute_centrality_endpoint(comparison: str):
    precompute(comparison)
    return {'status': 'done'}

@app.get('/api/full_net')
def get_full_network(comparison: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT celltype FROM nodes WHERE comparison = %s;', (comparison,))
    celltypes = [row[0] for row in cur.fetchall()]
    cur.execute('SELECT COUNT(*) FROM nodes WHERE comparison = %s;', (comparison,))
    total_nodes = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM links WHERE comparison = %s;', (comparison,))
    total_links = cur.fetchone()[0]
    cur.close()
    
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM nodes WHERE comparison = %s;', (comparison,))
    nodes = cur.fetchall()
    #filter links by significance, OTHERWISE laptop runs out of memory (and non-significant LRs are useless)
    cur.execute('SELECT * FROM links WHERE (significance < 0.05 OR significance IS NULL) AND comparison = %s;', (comparison,))
    links = cur.fetchall()
    cur.close()
    conn.close()
    #remove nodes that do NOT appear in any link
    if links:
        connected_ids = {l['source'] for l in links} | {l['target'] for l in links}
        nodes = [n for n in nodes if n['id'] in connected_ids]
    else:
        nodes = []
    moltype_counts = Counter(n['moltype'] for n in nodes)
    link_type_counts = Counter(l['type'] for l in links)
    b_outlier_threshold = min((n['betweenness'] for n in nodes if n['is_outlier_b']), default=0)
    p_outlier_threshold = min((n['pagerank'] for n in nodes if n['is_outlier_p']), default=0)

    node_map = {n['id']: n for n in nodes}
    # compute data for heatmaps 
    lr_counts: dict[tuple[str, str], int] = Counter()
    tfl_counts: dict[str, int] = Counter()
    rtf_counts: dict[str, int] = Counter()
    
    for l in links:
        src = node_map.get(l['source'])
        tgt = node_map.get(l['target'])
        if l['type'] == 'LR':        
            if src and tgt:
                lr_counts[(src['celltype'], tgt['celltype'])] += 1
        elif l['type'] == 'TFL':
            tfl_counts[src['celltype']] += 1
        else:
            rtf_counts[tgt['celltype']] += 1
    celltypes = sorted({ct for pair in lr_counts for ct in pair})
    lr_heatmap = [
        {'sender': s, 'receiver': r, 'count': lr_counts.get((s, r), 0)}
        for s in celltypes
        for r in celltypes
    ]
    # marginal sums for the bars
    lr_sender_totals = {s: sum(lr_counts.get((s, r), 0) for r in celltypes) for s in celltypes}
    lr_receiver_totals = {r: sum(lr_counts.get((s, r), 0) for s in celltypes) for r in celltypes}

    b_topMols = [n['name'] for n in sorted(nodes, key=lambda n: (n['betweenness']or 0 ), reverse=True)]
    b_topMols = list(dict.fromkeys(b_topMols))[:5] #keep order but remove duplicates 
    p_topMols = list(dict.fromkeys([n['name'] for n in sorted(nodes, key=lambda n: (n['pagerank'] or 0), reverse=True)]))[:5]

    return {'nodes': nodes, 
            'links': links, 
            'stats': {
                'nNodes': len(nodes),
                'nLigands': moltype_counts.get('ligand', 0),
                'nReceptors': moltype_counts.get('receptor', 0),
                'nTFs': moltype_counts.get('TF', 0),
                'nLinks': len(links),
                'nLRLinks': link_type_counts.get('LR', 0),
                'nTFLLinks': link_type_counts.get('TFL', 0),
                'nRTFLinks': link_type_counts.get('RTF', 0),
                'b_outlierThreshold': b_outlier_threshold,
                'p_outlierThreshold': p_outlier_threshold,
                'b_topMols': b_topMols,
                'p_topMols': p_topMols
            },
            'total_nodes' : total_nodes,
            'total_links' : total_links,
            'celltypes' : celltypes,
            'heatmaps' : {
                'lr_heatmap' : {
                    'data': lr_heatmap,
                    'sender_totals': lr_sender_totals,
                    'receiver_totals': lr_receiver_totals,
                },
                'tfl_heatmap' : { 'data' : tfl_counts },
                'rtf_heatmap' : { 'data' : rtf_counts }
            }
        }

@app.get('/api/filtered_data')
def get_filtered_network(
    comparison: str = None,
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
        WHERE comparison = %s AND celltype IN (%s, %s)
    """
    params = [comparison, sender, receiver]

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
                AND (
                    l.type != 'LR'
                    OR ns.celltype != nt.celltype
                    )
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
def get_molecules_names_list(comparison: str, q: str = ''):
    conn = get_db_connection()
    cur = conn.cursor()
    if q:
        cur.execute(
            """SELECT DISTINCT name, celltype, verbose_id
               FROM nodes
               WHERE comparison = %s AND name ILIKE %s
               ORDER BY name ASC;""",
            (comparison, f'%{q}%')
        )
    else:
        cur.execute(
            """SELECT DISTINCT name, celltype, verbose_id
               FROM nodes
               WHERE comparison = %s
               ORDER BY name ASC;""",
            (comparison,)
        )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {
        'molecules': [
            {'name': r[0], 'celltype': r[1], 'verbose_id': r[2]}
            for r in rows
        ]
    }
