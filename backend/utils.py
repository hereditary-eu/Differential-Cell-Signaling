import pandas as pd

def sanitizeCelltypes(ccc : pd.DataFrame, tfl : pd.DataFrame, ref_file : str):
    print('Sanitizing cell type names based on reference file')
    try:
        ref_df = pd.read_csv(ref_file)
    except Exception as e:
        raise ValueError(f"Unable to read reference file: {repr(e)}")
    print(f"Reference dataframe :\n{ref_df}")
    
    ref_df["newName"] = ref_df["newName"].astype(str).str.strip().str.replace("'", "")
    ref_df["oldName"] = ref_df["oldName"].astype(str).str.strip().str.replace("'", "")
    ref_df = ref_df.dropna(subset=['newName'])
    ref_df = ref_df[ref_df['newName'] != '']
    
    mapping = dict(zip(ref_df['oldName'], ref_df['newName']))
    print(f"Mapping: {mapping}")
    
    def clean_map(series, mapping, colname):
        count_before = len(series)
        series = series.astype(str).str.strip().str.replace("'", "")
        series = series.replace(mapping)
        series = series.replace({'na':None, 'None':None, 'nan':None, 'NaN':None})
        n_missing = series.isna().sum()
        if n_missing:
            print(f"{n_missing} rows with unmapped or missing {colname}")
        return series

    ccc['sender'] = clean_map(ccc['sender'], mapping, 'sender')
    ccc['receiver'] = clean_map(ccc['receiver'], mapping, 'receiver')
    tfl['cellType'] = clean_map(tfl['cellType'], mapping, 'cellType')

    ccc_before = len(ccc)
    ccc = ccc.dropna(subset=['sender', 'receiver']).reset_index(drop=True)
    
    tfl_before = len(tfl)
    tfl = tfl.dropna(subset=['cellType']).reset_index(drop=True)

    print(f"Dropped {ccc_before - len(ccc)} rows from CCC and {tfl_before - len(tfl)} from TFL due to missing cell types")

    return ccc, tfl


def extract_rtf(ccc : pd.DataFrame):
    required_cols = ["receptor", "receiver", "tfactors", "S_intra"]
    missing = [c for c in required_cols if c not in ccc.columns]
    if missing:
        raise ValueError(f"Input CCC dataframe is missing required columns: {missing}")
    
    rtf = ccc[required_cols].drop_duplicates()
    
    rtf_nodes = []
    rtf_links = []

    for i, row in rtf.iterrows():
        if pd.isna(row["tfactors"]):
            continue #skip if no tfactors listed

        rtf_nodes.append({
                "name": row["receptor"],
                "moltype": "receptor",
                "celltype": row["receiver"],
                "intrascore": row["S_intra"]
            })
        
        for tf in row["tfactors"].split(","):
            rtf_nodes.append({
                    "name": tf,
                    "moltype": "TF",
                    "celltype": row["receiver"],
                    "intrascore": None
                })
            rtf_links.append({
                    "from": row["receptor"]+"__"+row["receiver"]+"__receptor",
                    "to": tf+"__"+row["receiver"]+"__TF",
                    "type": "RTF",
                    "weight": None,
                    "significance": None,
                    "layer": 3
                })
            
    rtf_nodes = pd.DataFrame(rtf_nodes).drop_duplicates().reset_index(drop=True)
    rtf_links = pd.DataFrame(rtf_links).drop_duplicates().reset_index(drop=True)
    return rtf_nodes, rtf_links

def extract_ccc(ccc : pd.DataFrame, conditions = ["cond", "ref"], pval_col = "pvalue_adj_S_inter"):
    required_cols = ["ligand", "receptor", "sender", "receiver", "S_intra"]
    col_cond = f"S_inter_{conditions[0]}"
    col_ref = f"S_inter_{conditions[1]}"
    # validate columns 
    missing = [c for c in required_cols + [pval_col] + [col_cond, col_ref] if c not in ccc.columns]
    if missing:
        raise ValueError(f"Input dataframe is missing required columns: {missing}")

    cols = required_cols + [pval_col] + [col_cond, col_ref]

    ccc_nodes = []
    ccc_links = []
    for i, row in ccc[cols].drop_duplicates().iterrows(): #drop_duplicates should be unnecessary, but just in case
        # using pd.concat is less efficient! than appending to a list and creating a df at the end, but more readable
        ccc_nodes.append({
                "name": row["ligand"],
                "moltype": "ligand",
                "celltype": row["sender"],
                "intrascore": None
            })
        ccc_nodes.append({
                "name": row["receptor"],
                "moltype": "receptor",
                "celltype": row["receiver"],
                "intrascore": row["S_intra"]
            })
        ccc_links.append({
                "from": row["ligand"]+"__"+row["sender"]+"__ligand",
                "to": row["receptor"]+"__"+row["receiver"]+"__receptor",
                "type": "LR",
                "weight": row[col_cond] - row[col_ref], #difference in inter score between conditions
                "significance": row[pval_col],
                "layer": 2
            })

    ccc_nodes = pd.DataFrame(ccc_nodes).drop_duplicates().reset_index(drop=True)
    ccc_links = pd.DataFrame(ccc_links).drop_duplicates().reset_index(drop=True)

    return ccc_nodes, ccc_links

def extract_tfl(tfl : pd.DataFrame, tf_db : pd.DataFrame, ccc : pd.DataFrame, cond_colname : str, score_colname = "consensus_mean"):
    # tfl columns: Condition, cellType, TF, consesus_mean
    # tf_db columns: source (TF), target (gene), weight (1 or -1)  (in older versions, weight was called mor)
    
    # steps:
    # filter tf_db to only include TFs present in tfl
    # join (filtered) tf_db with ccc on L name
    # create nodes and links dataframes
    # tf_db_filt = tf_db[tf_db['source'].isin(set(tfl['TF']))] #filter tf_db on diff TFs results
    required_cols = [cond_colname, "cellType", "TF", score_colname]
    missing = [c for c in required_cols if c not in tfl.columns]
    if missing:
        raise ValueError(f"Input TFL dataframe is missing required columns: {missing}\n Found columns: {tfl.columns.tolist()}")
    tfl = tfl[required_cols]

    required_cols = ['source', 'target', 'weight']
    missing = [c for c in required_cols if c not in tf_db.columns]
    if missing:
        raise ValueError(f"Input TF-DB dataframe is missing required columns: {missing}\n Found columns: {tf_db.columns.tolist()}")
    tf_db = tf_db[required_cols]
    
    # tfl = tfl.drop(columns=[cond_colname, score_colname]).drop_duplicates() # at least for now, we dont consider score and condition columns, since results are already filtered; drop duplicates
    tf_db_filt = tf_db[(tf_db['target'].isin(set(ccc['ligand']))) &     #eventually, filter both on target genes encoding for ligands present in diff ccc results
                        (tf_db['source'].isin(set(tfl['TF'])))]           #and on diff TFs resutls

    tf_db_filt = tf_db_filt.rename(columns={'source':'TF'}) # dict {'old_name':'new_name'}
    tf_links = pd.merge(tfl, tf_db_filt, on = 'TF', how = 'left') #join on TF name, this will repeat links for every celltype in which TF is active
    tf_links = tf_links.dropna(subset=['target']) #drop rows where TF has no target in tf_db_filt 

    tf_links['from'] = tf_links['TF'] + '__' + tf_links['cellType'] + '__TF'
    tf_links['to'] = tf_links['target'] + '__' + tf_links['cellType'] + '__ligand'
    tf_links['type'] = 'TFL'
    tf_links['layer'] = 1
    tf_links['significance'] = None #no significance for TFL links from decoupleR
    
    #for now, only keep tf_nodes and ignore ligand nodes, which are taken from CCC
    tf_nodes = tf_links[['TF', 'cellType']].drop_duplicates().reset_index(drop=True)
    tf_nodes = tf_nodes.rename(columns={'TF':'name', 'cellType':'celltype'})
    tf_nodes['moltype'] = 'TF'
    tf_nodes['intrascore'] = None #no intrascore for TF nodes for now (eventually in the future store differential TF activity value)

    return tf_nodes, tf_links[['from', 'to', 'type', 'weight', 'layer', 'significance']]


def annotate_bothLR_nodes(nodes : pd.DataFrame):
    #find set of receptors, intersect with set of ligands
    bothLR = set(nodes[nodes['moltype']=='receptor']['name']).intersection(set(nodes[nodes['moltype']=='ligand']['name']))
    to_drop = []
    num_receptors_bothLR = 0
    num_ligands_bothLR = 0
    for i,row in nodes.iterrows():
        if row['name'] in bothLR:
            if row['moltype'] == 'ligand':
                #drop ligand node, will be replaced by bothLR node
                to_drop.append(i)
                num_ligands_bothLR += 1
            else:
                num_receptors_bothLR += 1
                nodes.iloc[i, nodes.columns.get_loc('moltype')] = 'bothLR' #check if this works as intended
    nodes = nodes.drop(index=to_drop).reset_index(drop=True)
    print(f"Annotated {num_receptors_bothLR} receptor nodes as bothLR and removed {num_ligands_bothLR} ligand nodes")
    return nodes


def aggregate_full_net(ccc : pd.DataFrame, tfl : pd.DataFrame, tf_db : pd.DataFrame, conditions : list, cond_colname = "Genotype"):
    ccc_nodes, ccc_links = extract_ccc(ccc, conditions = conditions) #in the future, pass col names for case study flexibility
    print('CCC extraction done')
    tfl_nodes, tfl_links = extract_tfl(tfl, tf_db, ccc, cond_colname) #in the future, pass col names for case study flexibility
    print('TFL extraction done')
    rtf_nodes, rtf_links = extract_rtf(ccc)
    print('RTF extraction done')

    all_links = pd.concat([tfl_links, ccc_links, rtf_links], ignore_index=True).drop_duplicates().reset_index(drop=True)
    all_nodes = pd.concat([tfl_nodes, ccc_nodes, rtf_nodes], ignore_index=True).drop_duplicates().reset_index(drop=True)
    #FOR DEBUGGING
    all_nodes.to_csv('all_nodes_debug.csv', index=False)
    all_links.to_csv('all_links_debug.csv', index=False)
    # print('Aggregation and bothLR nodes annotation done')

    return all_nodes, all_links