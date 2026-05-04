from fastapi import FastAPI
from fastapi import Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras
from typing import Literal
import statistics
import networkx as nx
from collections import Counter, defaultdict, deque
from itertools import islice

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

# benedikt if u see this, it's just temporary!!!! :) i'll switch to puppygraph. es tut mir leid
def normalize_cycle(cycle: list) -> tuple:
    """Normalize a cycle to remove rotational duplicates."""
    min_index = cycle.index(min(cycle))
    return tuple(cycle[min_index:] + cycle[:min_index])

def build_graph(nodes: list, links: list) -> nx.DiGraph:
    """
    Build a directed graph where:
    - LR links are bidirectional (added in both directions)
    - TFL and RTF links are directed
    """
    G = nx.DiGraph()
    node_ids = {n['id'] for n in nodes}
    G.add_nodes_from(node_ids)

    for l in links:
        src, tgt, ltype = l['source'], l['target'], l['type']
        if src not in node_ids or tgt not in node_ids:
            continue
        G.add_edge(src, tgt, type=ltype, weight=l.get('weight'), id=l.get('id'))
        if ltype == 'LR':
            G.add_edge(tgt, src, type=ltype, weight=l.get('weight'), id=l.get('id'), reversed=True)
    return G

def find_cycles(nodes: list, links: list, max_cycle_length: int = 10, max_cycles: int = 500) -> dict:
    """
    max_cycle_length: cap on cycle length to avoid explosion (default 10)
        max_cycles: maximum number of cycles to return (default 500)
    Returns dict with cycles list and stats
    """
    if not nodes or not links:
        return {'cycles': [], 'nCycles': 0, 'truncated': False}
    G = build_graph(nodes, links)

    #Johnson's algorithm for sparse graphs
    seen = set()
    cycles = []
    truncated = False
    raw_gen = nx.simple_cycles(G)

    for cycle in islice(raw_gen, max_cycle_length*10):
        if len(cycle) <= 2 or len(cycle) > max_cycle_length:
            continue
        key = normalize_cycle(cycle)
        if key in seen:
            continue
        seen.add(key)
        
        edges = []
        for i in range(len(cycle)):
            src = cycle[i]
            tgt = cycle[(i + 1) % len(cycle)]
            edge_data = G.get_edge_data(src, tgt) or {}
            edges.append({
                'source': src,
                'target': tgt,
                'type': edge_data.get('type'),
                'weight': edge_data.get('weight'),
                'id': edge_data.get('id'),
                'reversed': edge_data.get('reversed', False)
            })
        cycles.append({'nodes': list(key), 'edges': edges, 'length': len(key)})

        if len(cycles) >= max_cycles:
            truncated = True
            break
    cycles.sort(key=lambda c: c['length'])
    return {'cycles': cycles, 'nCycles': len(cycles), 'truncated': truncated}

@app.get("/api/cycles")
def get_cycles(
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
    inter_dir: Literal['up', 'down'] = 'up',
    max_cycle_length: int = 10,
    max_cycles: int = 500
):
    """
    Returns all simple cycles in the filtered network.
    LR links are treated as undirected; TFL and RTF as directed.
    """
    nodes, links = filter_network(
        comparison, sender, receiver, reverse_sig, filter_intrascore,
        filter_pv, filter_inter, min_intrascore, max_intrascore,
        pv_thresh, focus_on_LR, inter_dir
    )
    node_meta = {
        n['id']: {
            'name': n.get('name'),
            'celltype': n.get('celltype'),
            'moltype': n.get('moltype'),
            'betweenness': n.get('betweenness'),
            'pagerank': n.get('pagerank')
        }
        for n in nodes
    }
    edge_meta = {}
    for l in links:
        key = (l['source'], l['target'])
        edge_meta[key] = {
            'type':   l.get('type'),
            'weight': l.get('weight'),
        }
        if l.get('type') == 'LR':
            edge_meta[(l['target'], l['source'])] = {
                'type':     l.get('type'),
                'weight':   l.get('weight'),
                'reversed': True,
            }
    result = find_cycles(nodes, links, max_cycle_length=max_cycle_length, max_cycles=max_cycles)
    for cycle in result['cycles']:
        cycle['nodes'] = [
            {'id': nid, **node_meta.get(nid, {})}
            for nid in cycle['nodes']
        ]
        cycle['edges'] = [
            {
                'source':   e['source'],
                'target':   e['target'],
                'reversed': e.get('reversed', False),
                **edge_meta.get((e['source'], e['target']), {'type': e.get('type'), 'weight': None}),
            }
            for e in cycle['edges']
        ]
    return result

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
    
    top_sr = max(lr_counts, key=lr_counts.get, default=None)
    if top_sr:
        top_sender = top_sr[0]
        top_receiver = top_sr[1]
    else: 
        top_sender = top_receiver = None
    
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
            },
            'initialize' : {
                'sender': top_sender,
                'receiver': top_receiver
            }
        }


def filter_network(
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
    inter_dir: Literal['up', 'down'] = 'up'):

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
    
    cur.close()
    conn.close()

    return filtered_nodes, links

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
    nodes, links = filter_network(
        comparison, sender, receiver, reverse_sig, filter_intrascore, filter_pv, filter_inter,
        min_intrascore, max_intrascore, pv_thresh, focus_on_LR, inter_dir
    )
    stats = {
        'nNodes': len(nodes),
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
    for n in nodes:
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

    return {
        'nodes': nodes,
        'links': links,
        'stats': stats,
        'p_top3Mols': sorted(nodes, key=lambda n: (n['pagerank'] or 0), reverse=True)[:3],
        'b_top3Mols': sorted(nodes, key=lambda n: (n['betweenness'] or 0), reverse=True)[:3]
    }

@app.get('/api/neighborhood')
def get_node_neighborhood(
    root_id: str,
    max_steps: int = 4,
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
    root_id_int = int(root_id)

    result = filter_network(
        comparison, sender, receiver, reverse_sig, filter_intrascore, filter_pv, filter_inter,
        min_intrascore, max_intrascore, pv_thresh, focus_on_LR, inter_dir
    )

    # filter_network can return a dict on empty result
    if isinstance(result, dict):
        return {'nodes': [], 'links': [], 'rootId': root_id_int}
    nodes, links = result

    adj = defaultdict(set)
    for l in links:
        src, tgt = l['source'], l['target']
        adj[src].add(tgt)
        adj[tgt].add(src)  # always add reverse: ALL LINKS AS UNDIRECTED

    # BFS from root
    visited = {root_id_int: 0}
    queue = deque([root_id_int])

    while queue:
        current = queue.popleft()
        dist = visited[current]
        if dist >= max_steps:
            continue
        for neighbor in adj.get(current, []):
            if neighbor not in visited:
                visited[neighbor] = dist + 1
                queue.append(neighbor)

    neighbor_ids = list(visited.keys())

    if not neighbor_ids:
        return {'nodes': [], 'links': [], 'rootId': root_id_int}

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        "SELECT * FROM nodes WHERE id = ANY(%s::integer[]) AND comparison = %s",
        [neighbor_ids, comparison]
    )
    db_nodes = cur.fetchall()

    nodes_out = []
    for n in db_nodes:
        nd = dict(n)
        nd['distance'] = visited.get(n['id'], 999)
        nodes_out.append(nd)

    valid_ids = {n['id'] for n in nodes_out}

    subgraph_links = []
    seen_pairs = set()
    for l in links:
        src, tgt = l['source'], l['target']
        if src in valid_ids and tgt in valid_ids:
            pair = (min(src, tgt), max(src, tgt))
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                subgraph_links.append(dict(l))

    cur.close()
    conn.close()

    return {
        'nodes': nodes_out,
        'links': subgraph_links,
        'rootId': root_id_int
    }

@app.get('/api/molecules_names_list')
def get_molecules_names_list(comparison: str, q: str = ''):
    conn = get_db_connection()
    cur = conn.cursor()
    if q:
        cur.execute(
            """SELECT DISTINCT name, celltype, verbose_id, id
               FROM nodes
               WHERE comparison = %s AND name ILIKE %s
               ORDER BY name ASC;""",
            (comparison, f'%{q}%')
        )
    else:
        cur.execute(
            """SELECT DISTINCT name, celltype, verbose_id, id
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
            {'name': r[0], 'celltype': r[1], 'verbose_id': r[2], 'id': r[3]}
            for r in rows
        ]
    }
