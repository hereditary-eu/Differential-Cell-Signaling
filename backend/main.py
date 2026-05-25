from fastapi import FastAPI, HTTPException, Query #, APIRouter, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import psycopg2
import psycopg2.extras
from typing import Literal, List, Optional
import statistics
import networkx as nx
from collections import Counter, defaultdict, deque
import pandas as pd
from gprofiler import GProfiler
# import shutil
# from pathlib import Path
import os
# router = APIRouter()
app = FastAPI()
# app.include_router(router, prefix='/api')
origins = ['http://localhost:5173', 'http://127.0.0.1:5173'] #allow frontend to connect #ATTENTION: if backend is run as 127.0.0.1, CORS error arises! so use 0.0.0.0
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
        dbname=os.getenv('DB_NAME', 'diffcellsig'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASS', 'postgres'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )
def normalize_cycle(cycle: list) -> tuple:
    """Normalize a cycle to remove rotational duplicates."""
    rotations = [cycle[i:] + cycle[:i] for i in range(len(cycle))]
    rev = cycle[::-1]
    rev_rotations = [rev[i:] + rev[:i] for i in range(len(rev))]
    return tuple(min(rotations + rev_rotations))

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

    for cycle in nx.simple_cycles(G):
        if len(cycle) < 3 or len(cycle) > max_cycle_length:
            continue
        if not all( #check that the cycle is actually closed
            G.has_edge(cycle[i], cycle[(i + 1) % len(cycle)])
            for i in range(len(cycle))
        ):
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
    # k=min(n,500) approximation for large graphs
    n_nodes = G.number_of_nodes()
    k = min(n_nodes, 500) if n_nodes > 500 else None
    betweenness = nx.betweenness_centrality(G, k=k, normalized=True, seed = 23)
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
    # filter_celltypes: bool = True,
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
    filterTFs: bool = False):

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    #get all potential nodes + filter by intrascore
    # if filter_celltypes:
    node_query = """
        SELECT * FROM nodes
        WHERE comparison = %s AND celltype IN (%s, %s)
    """
    params = [comparison, sender, receiver]
    # else:
    # node_query = """
    #     SELECT * FROM nodes
    #     WHERE comparison = %s
    # """
    # params = [comparison]
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

    if filterTFs:    #keep only TFs involved in TFL (i.e. derive from TF activity analysis)
        sig_tf_ids = {l['source'] for l in links if l['type'] == 'TFL'}
        links = [l for l in links if l['type'] == 'LR' or (l['type'] == 'RTF' and l['target'] in sig_tf_ids) or (l['type'] == 'TFL' and l['source'] in sig_tf_ids)]
    
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
    inter_dir: Literal['up', 'down'] = 'up',
    filterTFs: bool = False
):
    nodes, links = filter_network(
        comparison, sender, receiver, reverse_sig, filter_intrascore, filter_pv, filter_inter,
        min_intrascore, max_intrascore, pv_thresh, focus_on_LR, inter_dir, filterTFs
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
    inter_dir: Literal['up', 'down'] = 'up',
    filterTFs: bool = False
):
    root_id_int = int(root_id)

    result = filter_network(
        comparison, sender, receiver, reverse_sig, filter_intrascore, filter_pv, filter_inter,
        min_intrascore, max_intrascore, pv_thresh, focus_on_LR, inter_dir, filterTFs
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
def get_molecules_names_list(
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
    filterTFs: bool = False,
    q: str = ''
    ):
    nodes, links = filter_network(
        comparison, sender, receiver, reverse_sig, filter_intrascore, filter_pv, filter_inter,
        min_intrascore, max_intrascore, pv_thresh, focus_on_LR, inter_dir, filterTFs
    )
    rows = [(n['name'], n['celltype'], n['verbose_id'], n['id']) for n in nodes if q.lower() in n['name'].lower()]
    return {
        'molecules': [
            {'name': r[0], 'celltype': r[1], 'verbose_id': r[2], 'id': r[3]}
            for r in rows
        ]
    }


#start implementing GO Enrichment analysis
def get_genes_set(
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
    split_complexes: bool = False,
    subunits_delimiter: str = ','
    ) -> set:
    nodes, links = filter_network(
        comparison, sender, receiver, reverse_sig, filter_intrascore, filter_pv, filter_inter,
        min_intrascore, max_intrascore, pv_thresh, focus_on_LR, inter_dir, filterTFs=True
    )
    gene_names = set()
    if split_complexes:
        for n in nodes:
            for s in n['name'].split(subunits_delimiter):
                gene_names.add(s.strip())
    else:
        for n in nodes:
            gene_names.add(n['name'])
    return gene_names
 
def get_genes_from_db(DB: str, type: Literal['LR', 'TF_TG', 'RTF'], split_complexes: bool = False, subunits_delimiter: str = ',') -> set:
    """
    Column layout per DB type:
    - LR:    'ligand', 'receptor'  (may contain complex subunits)
    - TF_TG: 'source' (TF), 'target' (gene)
    - RTF:   'receptor', 'tf'
    """
    db = pd.read_csv(f'ref_db/{DB}.csv')
    if type == 'LR':
        if split_complexes:
            genes: set = set()
            for _, row in db.iterrows():
                for col in ['ligand', 'receptor']:
                    for s in str(row[col]).split(subunits_delimiter):
                        genes.add(s.strip())
            return genes
        return set(db['ligand'].astype(str)).union(set(db['receptor'].astype(str)))
    elif type == 'TF_TG':
        return set(db['source'].astype(str)).union(set(db['target'].astype(str)))
    else:  # RTF
        return set(db['receptor'].astype(str)).union(set(db['tf'].astype(str)))
 
def prepare_gene_universe(
    LR_DB: str,
    TF_DB: str,
    RTF_DB: str,
    use_lr: bool = True,
    use_tf: bool = True,
    use_rtf: bool = True,
    split_complexes: bool = False,
    subunits_delimiter: str = ','
) -> set:
    universe: set = set()
    if use_lr:
        universe.update(get_genes_from_db(LR_DB, 'LR', split_complexes, subunits_delimiter))
    if use_tf:
        universe.update(get_genes_from_db(TF_DB, 'TF_TG'))
    if use_rtf:
        universe.update(get_genes_from_db(RTF_DB, 'RTF'))
    return universe
 
def universe_sanity_check(universe: set, genes_in_network: set) -> dict:
    """
    Returns a warning dict if some query genes are absent from the universe,
    but does NOT raise — the caller decides whether to treat this as an error.
    """
    missing = genes_in_network - universe
    if missing:
        return {
            'status': 'warning',
            'missing_count': len(missing),
            'examples': sorted(missing)[:10],
            'message': (
                f"{len(missing)} network gene(s) are absent from the universe "
                f"(e.g. {', '.join(sorted(missing)[:5])}). "
                "They will be ignored by gProfiler."
            )
        }
    return {'status': 'ok', 'missing_count': 0, 'examples': [], 'message': ''}
 
def run_gprofiler(
    gene_list: list,
    organism: str,
    sources: list,
    background: Optional[list],
    significance_method: str,
    user_threshold: float,
) -> List[dict]:
    """ wrapper for gprofiler-official."""
    gp = GProfiler(return_dataframe=False)
    kwargs: dict = dict(
        query=gene_list,
        organism=organism,
        sources=sources,
        significance_threshold_method=significance_method,
        user_threshold=user_threshold,
        no_evidences=False, #this parameter allows to report which genes of query where found in the term
    )
    if background:
        kwargs["background"] = background
    return gp.profile(**kwargs)  # type: ignore[return-value]
 
def format_results(raw: List[dict]) -> List[dict]:
    """Trim & rename fields for the frontend."""
    keep = [
        "source", "native", "name", "p_value",
        "significant", "description",
        "term_size", "query_size", "intersection_size",
        "precision", "recall",
        "intersections",
    ]
    out = []
    for r in raw:
        row = {k: r.get(k) for k in keep}
        row["gene_ratio"] = (
            round(r["intersection_size"] / r["query_size"], 4)
            if r.get("query_size") else None
        )
        out.append(row)
    return out
 
@app.get('/api/go_enrichment')
def perform_go_enrichment(
    # network filtering
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
    # gene universe 
    split_complexes: bool = False,
    subunits_delimiter: str = ',',
    LR_DB: Literal[
        'LR_pairs_Lagger_2023_mouse',
        'LR_pairs_Lagger_2023_human',
        'LR_pairs_ConnectomeDB_2020',
        'LR_pairs_Skelly_2018_mouse'
    ] = 'LR_pairs_Lagger_2023_mouse',
    TF_DB: Literal[
        'collecTRI_mouse',
        'collecTRI_human',
        'TF_TG_TTRUSTv2_mouse',
        'TF_TG_TTRUSTv2_human'
    ] = 'collecTRI_mouse',
    RTF_DB: Literal[
        'TF_PPR_KEGG_human',
        'TF_PPR_KEGG_mouse'
    ] = 'TF_PPR_KEGG_mouse',
    use_lr: bool = True,
    use_tf: bool = True,
    use_rtf: bool = True,
    use_custom_universe: bool = False,
    custom_universe: List[str] = Query(default=[]),
    # gProfiler params 
    significance_method: Literal['g_SCS', 'bonferroni', 'fdr'] = 'g_SCS',
    pv_cutoff: float = 0.05,
    # repeated query-param: ?sources=GO:BP&sources=KEGG  OR comma-joined ?sources=GO:BP,KEGG
    sources: List[str] = Query(default=['GO:BP', 'GO:MF', 'GO:CC']),
    organism: Literal['hsapiens', 'mmusculus'] = 'mmusculus',
):
    gene_set: set = get_genes_set(
        comparison, sender, receiver, reverse_sig, filter_intrascore, filter_pv, filter_inter,
        min_intrascore, max_intrascore, pv_thresh, focus_on_LR, inter_dir,
        split_complexes, subunits_delimiter
    )
    if not gene_set:
        raise HTTPException(
            status_code=400,
            detail="No genes found in the filtered network. Please adjust your filters."
        )
 
    if use_custom_universe:
        if not custom_universe:
            raise HTTPException(
                status_code=400,
                detail="use_custom_universe=true but no genes were provided via custom_universe."
            )
        background_set: set = set()
        for entry in custom_universe:
            for g in entry.split(','):
                g = g.strip()
                if g:
                    background_set.add(g)
    else:
        try:
            background_set = prepare_gene_universe(
                LR_DB, TF_DB, RTF_DB, use_lr, use_tf, use_rtf,
                split_complexes, subunits_delimiter
            )
        except FileNotFoundError as e:
            raise HTTPException(status_code=500, detail=f"Reference DB file not found: {e}")
 
    sanity = universe_sanity_check(background_set, gene_set)
    # do NOT block on warnings — gProfiler can still run; missing genes are
    # simply not enriched. Only raise if the universe itself is empty.
    if not background_set:
        raise HTTPException(status_code=400, detail="Gene universe is empty.")
 
    # Flatten sources (frontend may send comma-joined or repeated params)
    source_list: list = []
    for entry in sources:
        for s in entry.split(','):
            s = s.strip()
            if s:
                source_list.append(s)
    if not source_list:
        raise HTTPException(status_code=400, detail="No annotation sources selected.")
 
    try:
        raw = run_gprofiler(
            gene_list=sorted(gene_set),
            organism=organism,
            sources=source_list,
            background=sorted(background_set),   # must be a list, not a set
            significance_method=significance_method,
            user_threshold=pv_cutoff,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"gProfiler error: {e}")
 
    res = format_results(raw)
    # print(res)
    return JSONResponse({
        "query_size": len(gene_set),
        "background_size": len(background_set),
        "n_significant": sum(1 for r in res if r["significant"]),
        "universe_warning": sanity['message'] if sanity['status'] == 'warning' else None,
        "results": res,
    })


#towards deployment
#tell fastapi to serve build/index.html for any route that is not an API endpoint
from fastapi.staticfiles import StaticFiles
app.mount('/', StaticFiles(directory='build', html=True), name = 'static')

# ----------------------------- TO DO
# user upload of case study
# def run_ingestion(tmp_dir: Path, case_study_name: str, condition: str, ref_condition: str, organism: Literal['human', 'mouse'], split_complexes: bool, sanitize: bool):
#     #split_complexes will be passed to dc.get_collectri
#     from .ingest import CaseStudy, Node, Link, DB_URL
#     import traceback
#     from sqlalchemy import create_engine
#     from sqlalchemy.orm import Session, declarative_base
#     try:
#         cs = CaseStudy(caseStudyName=case_study_name, conditions=[condition, ref_condition], organism=organism, split_complexes=split_complexes)
#         cs.load_data(ccc_filename='CCC.csv', tf_filename='TF.csv', files_path=tmp_dir)
#         if sanitize:
#             cs.sanitize_celltypes(ref_path=tmp_dir / 'sanitize.csv')
#         cs.aggregate_data()
#         print(cs.nodes.head())
        
#         Base = declarative_base()
#         engine = create_engine(DB_URL)
#         Base.metadata.create_all(engine)

#         with Session(engine) as session:
#             for _, n in cs.nodes.iterrows():
#                 session.add(Node(
#                     name=n['name'],
#                     celltype=n['celltype'],
#                     moltype=n['moltype'],
#                     intrascore=n['intrascore'],
#                     casestudy=n['casestudy'],
#                     comparison=n['comparison'],
#                     verbose_id=f"{n['name']}__{n['celltype']}__{n['moltype']}__{n['comparison']}"
#                 ))
#             session.flush()

#             db_nodes  = session.query(Node).filter_by(casestudy=case_study_name).all()
#             node_map  = {
#                 f"{n.name}__{n.celltype}__{n.moltype}__{n.comparison}": n.id
#                 for n in db_nodes
#             }

#             cs.links["source"] = cs.links["from"].map(node_map)
#             cs.links["target"] = cs.links["to"].map(node_map)
#             cs.links = cs.links.dropna(subset=["source", "target"])

#             for _, l in cs.links.iterrows():
#                 #unnecessary to add drow for user-given data (arbitrary choice)
#                 session.add(Link(
#                     source=int(l['source']),
#                     target=int(l['target']),
#                     type=l['type'],
#                     weight=float(l['weight']),
#                     significance=float(l['significance']),
#                     casestudy=cs.casestudy,
#                     comparison=cs.comparison
#                 ))
#             session.commit()
#         print(f"[upload] Ingestion complete for {case_study_name}")
#     except Exception:
#         traceback.print_exc()         # eventually to do: log this exception in a file
#     finally:
#         shutil.rmtree(tmp_dir)

# # The HTTP 202 Accepted successful response status code indicates that a request has been accepted for processing, but processing has not been completed or may not have started.
# # The HTTP 422 Unprocessable Entity status code indicates that while your API request was well-formed and syntactically valid, the server couldn't process it due to semantic or business logic errors in the request body. 
# @router.post('/upload_case_study', status_code=202)
# async def upload_case_study(
#     background_tasks: BackgroundTasks,
#     case_study_name: str = Form(...),
#     condition: str = Form(...),
#     ref_condition: str = Form(...),
#     organism: Literal['human', 'mouse'] = Form(...),
#     split_complexes: bool = Form(False),
#     ccc_file: UploadFile = File(...),
#     tf_file: UploadFile = File(...),
#     sanitize_file: UploadFile | None = File(None)
# ):
#     import re
#     for f in [case_study_name, condition, ref_condition]:
#         if not re.fullmatch(r"[a-zA-Z0-9\-]+", f):
#             raise HTTPException(status_code=422, detail=f"Invalid {f}. Only letters, numbers and hyphens (-) are allowed. ")
#     if organism not in ['human', 'mouse']:
#         raise HTTPException(status_code=422, detail="Invalid organism. Must be 'human' or 'mouse'.") #this is not really necessary, eventually remove it
#     if condition == ref_condition:
#         #this is very dumb
#         raise HTTPException(status_code=422, detail="Condition and reference condition cannot be the same.")
#     for f in (ccc_file, tf_file):
#         if f.content_type != 'text/csv': #this is not really necessary, eventually remove it (Svelte should also take care of it)
#             raise HTTPException(status_code=422, detail=f"Invalid file type for {f.filename}. Only CSV files are accepted." ) 

#     import tempfile
#     tmp_dir = Path(tempfile.mkdtemp(prefix = 'diffcellsig_upload_')) #save files to temporary directory, delete it after ingestion
#     try:
#         for upload, name in [(ccc_file, 'CCC.csv'), (tf_file, 'TF.csv')]:
#             content = await upload.read()
#             (tmp_dir / name).write_bytes(content)
#         if sanitize_file is not None:
#             content = await sanitize_file.read()
#             (tmp_dir / 'sanitize.csv').write_bytes(content)
#     except Exception as e:
#         shutil.rmtree(tmp_dir, ignore_errors=True)
#         raise HTTPException(status_code=500, detail=f"Failed to save files to temporary directory: {e}")
    
#     background_tasks.add_task(
#         run_ingestion,
#         tmp_dir = tmp_dir,
#         case_study_name = case_study_name,
#         condition = condition,
#         ref_condition = ref_condition,
#         organism = organism,
#         split_complexes = split_complexes,
#         sanitize = sanitize_file is not None
#     )
#     return JSONResponse(
#         status_code=202,
#         content={
#             'message': 'Upload received. Ingestion running in background.',
#             'caseStudy': case_study_name,
#             'comparison': f"{condition}_vs_{ref_condition}"
#         }
#     )