import pandas as pd
import numpy as np
from sqlalchemy import create_engine, Column, Integer, Float, String, ForeignKey
from sqlalchemy.orm import Session, relationship, declarative_base
import sys
from pathlib import Path
from .utils import aggregate_full_net, find_cycles, expand_links_dataframe
import decoupler as dc

DB_URL = 'postgresql+psycopg://postgres:postgres@localhost:5436/diffCellSig'
Base = declarative_base() #serves as a factory for mapping Python classes to db tables in an ORM

# TO DO: implement ingestion for user-uploaded case study

class Link(Base):
    __tablename__ = 'links'
    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    source = Column(Integer, ForeignKey('nodes.id'))
    target = Column(Integer, ForeignKey('nodes.id'))

    #link attributes
    type = Column(String) #link type: LR, TFL, RTF
    weight = Column(Float) #link weight/score this will be different for each link type: LR [0,1], TFL [-1;1], RTF [null, 1]
    significance = Column(Float) #p-value or adjusted p-value, applicable only for LR
    layer = Column(Integer) #1 for TFL, 2 for LR (CCC), 3 for RTF 
    detailed_type = Column(String) 
    casestudy = Column(String)
    comparison = Column(String) 
    #relationships
    from_node = relationship("Node", back_populates="outgoing_links", foreign_keys=[source])
    to_node = relationship("Node", back_populates="incoming_links", foreign_keys=[target])

class Node(Base):
    __tablename__ = 'nodes'
    #nodes attributes
    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    name = Column(String, nullable=False)
    celltype = Column(String, nullable=False) 
    moltype = Column(String, nullable=False) #general type: ligand, receptor, TF     # TODO: how to solve bothLR nodes? currently annotated as bothLR from function called in aggregate_full_net
    intrascore = Column(Float) #for receptor nodes
    verbose_id = Column(String, unique=True) #name__cellType to uniquely identify nodes before ids are generated 
    casestudy = Column(String)
    comparison = Column(String) 
    #relationships
    outgoing_links = relationship("Link", back_populates="from_node", foreign_keys=[Link.source])
    incoming_links = relationship("Link", back_populates="to_node", foreign_keys=[Link.target])

class CaseStudy():
    def __init__(self, caseStudyName, conditions,  organism, split_complexes):
        self.caseStudyName = caseStudyName
        self.conditions = conditions
        self.organism = organism
        self.split_complexes = split_complexes

    def load_data(self, ccc_filename, tf_filename):
        cwd = Path(__file__).parent.resolve()
        try:
            self.ccc = pd.read_csv(cwd / 'data' / self.caseStudyName / ccc_filename) # CCI results
            self.tf = pd.read_csv(cwd / 'data' / self.caseStudyName / tf_filename) #TF activity results
        except Exception as e:
            print('Unable to access csv file', repr(e))
            sys.exit(1)
        print('CSV files successfully loaded')
        if 'caseStudy' not in self.ccc.columns:
            self.ccc['caseStudy'] = self.caseStudyName
        if 'caseStudy' not in self.tf.columns:
            self.tf['caseStudy'] = self.caseStudyName
        if 'comparison' not in self.ccc.columns:
            self.ccc['comparison'] = self.conditions[0] + '_vs_' + self.conditions[1]
        if 'comparison' not in self.tf.columns:
            self.tf['comparison'] = self.conditions[0] + '_vs_' + self.conditions[1]
        else:
            self.tf = self.tf[self.tf['comparison'] == self.conditions[0] + '_vs_' + self.conditions[1]] # for ALS, all comparisons for tfs are in the same file for simplicity
        #check cell types match between ccc and tfl
        # ccc_celltypes = set(self.ccc['sender']).union(set(self.ccc['receiver']))
        # tf_celltypes = set(self.tf['cellType'])
        # if ccc_celltypes.difference(tf_celltypes):
        #     raise ValueError('Cell types in CCC and TFL results do not match')
        
    def sanitize_celltypes(self):
        cwd = Path(__file__).parent.resolve()
        if Path.exists(cwd / 'data' / self.caseStudyName / 'sanitizeCelltypes.csv'):
            print('Sanitizing cell type names based on reference file')
        try:
            ref_df = pd.read_csv(cwd / 'data' / self.caseStudyName / 'sanitizeCelltypes.csv')
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
            # count_before = len(series)
            series = series.astype(str).str.strip().str.replace("'", "")
            series = series.replace(mapping)
            series = series.replace({'na':None, 'None':None, 'nan':None, 'NaN':None})
            n_missing = series.isna().sum()
            if n_missing:
                print(f"{n_missing} rows with unmapped or missing {colname}")
            return series
        self.ccc['sender'] = clean_map(self.ccc['sender'], mapping, 'sender')
        self.ccc['receiver'] = clean_map(self.ccc['receiver'], mapping, 'receiver')
        self.tf['cellType'] = clean_map(self.tf['cellType'], mapping, 'cellType')
        ccc_before = len(self.ccc)
        self.ccc = self.ccc.dropna(subset=['sender', 'receiver']).reset_index(drop=True)
        tf_before = len(self.tf)
        self.tf = self.tf.dropna(subset=['cellType']).reset_index(drop=True)
        print(f"Dropped {ccc_before - len(self.ccc)} rows from CCC and {tf_before - len(self.tf)} from TFL due to missing cell types")

    def aggregate_data(self):
        tf_db = dc.get_collectri(organism = self.organism, split_complexes = self.split_complexes)
        tf_db = tf_db[
        (tf_db['source'].isin(self.tf['TF'].unique())) &
        (tf_db['target'].isin(self.ccc['ligand'].unique()))]
        self.nodes, self.links = aggregate_full_net(self.ccc, self.tf, tf_db, conditions = self.conditions, comparison = self.conditions[0] + '_vs_' + self.conditions[1])
        #NaN from pandas or numpy cannot be serialized, causing Internal Server Errors
        self.links = self.links.replace({np.nan: None})
        self.nodes = self.nodes.replace({np.nan: None})
        self.nodes['casestudy'] = self.caseStudyName
        self.nodes['comparison'] = self.conditions[0] + '_vs_' + self.conditions[1]
        self.links['casestudy'] = self.caseStudyName
        self.links['comparison'] = self.conditions[0] + '_vs_' + self.conditions[1]

def main():
    fmd = CaseStudy(caseStudyName='FMD', conditions=['Ko','Wt'], organism='mouse', split_complexes=False)
    fmd.load_data(ccc_filename='CCC.csv', tf_filename='TF.csv')
    fmd.sanitize_celltypes()
    fmd.aggregate_data()

    c9als_pn = CaseStudy(caseStudyName='ALS', conditions=['C9ALS', 'PN'], organism='human', split_complexes=False)
    c9als_pn.load_data(ccc_filename='CCC_subset_C9ALS_vs_PN.csv', tf_filename='TF_als.csv')
    c9als_pn.aggregate_data()

    sals_pn = CaseStudy(caseStudyName='ALS', conditions=['SALS', 'PN'], organism='human', split_complexes=False)
    sals_pn.load_data(ccc_filename='CCC_subset_SALS_vs_PN.csv', tf_filename='TF_als.csv')
    sals_pn.aggregate_data()

    sals_c9als = CaseStudy(caseStudyName='ALS', conditions=['SALS', 'C9ALS'], organism='human', split_complexes=False)
    sals_c9als.load_data(ccc_filename='CCC_subset_SALS_vs_C9ALS.csv', tf_filename='TF_als.csv')
    sals_c9als.aggregate_data()

    nodes = pd.concat([fmd.nodes, c9als_pn.nodes, sals_pn.nodes, sals_c9als.nodes]).drop_duplicates().reset_index(drop=True)
    links = pd.concat([fmd.links, c9als_pn.links, sals_pn.links, sals_c9als.links]).drop_duplicates().reset_index(drop=True)
    print(nodes.head())
    print(links.head())
    # sys.exit(0)
    #create db engine
    try:
        engine = create_engine(DB_URL, echo=True) 
        print('Database engine created')
    except Exception as e:
        print('Unable to access database', repr(e))
        sys.exit(1)
    
    # delete old tables #not sure if this is necessary
    Base.metadata.drop_all(engine, tables=[Base.metadata.tables["nodes"], Base.metadata.tables["links"]])
    # Create new tables
    Base.metadata.create_all(engine)
    print('Tables created (if not already present)')

    #populate tables
    session = Session(engine)
    print('Session created')

    try: 
        #iterate through dataframes and add to session
        #ids are automatically generated by sqlalchemy, with autoincrement
        print('\nPopulating tables...')
        for i,row in nodes.iterrows():
            v = Node(name=row['name'], celltype=row['celltype'], moltype=row['moltype'], intrascore=row['intrascore'], 
                     casestudy=row['casestudy'], comparison=row['comparison'],
                     verbose_id = f"{row['name']}__{row['celltype']}__{row['moltype']}__{row['comparison']}")
            session.add(v)
        try:
            session.flush() #this creates ids
            print('Vertices added to session')
        except Exception as e:
            session.rollback()
            raise ValueError('Unable to flush session after adding nodes\n', repr(e))
        
        db_nodes = session.query(Node).all() 

        node_map = { f"{n.name}__{n.celltype}__{n.moltype}__{n.comparison}": n.id for n in db_nodes }
        print('Node map created')
        
        links['source'] = links['from'].map(node_map)
        links['target'] = links['to'].map(node_map)
        
        # drop links where either source or target is NaN
        links = links.dropna(subset=['source', 'target']).reset_index(drop=True)

        # find all TF nodes that are still used in links
        # used_node_ids = set(links['source']).union(set(links['target']))
        # nodes = nodes[nodes['id'].isin(used_node_ids)].reset_index(drop=True)
        # session.flush() #flush again to update node ids after dropping unused nodes

        print('Links mapped to nodes ids')
        print("Unmapped sources:", links['source'].isna().sum())
        print("Unmapped targets:", links['target'].isna().sum())
        print(links[links['target'].isna()])
        print("Max source:", links['source'].max())
        print("Max target:", links['target'].max()) 
        print("Min source:", links['source'].min())
        print("Min target:", links['target'].min())

        for i, row in links.iterrows():
            if row['type'] == 'TFL':
                if row['weight'] > 0:
                    dtype = 'TF promotes expression of target ligand-encoding gene'
                else:
                    dtype = 'TF inhibits expression of target ligand-encoding gene'
            else:
                dtype = row['type']

            e = Link(type=row['type'], weight=row['weight'], significance=row['significance'], layer=row['layer'], 
                        casestudy=row['casestudy'], comparison=row['comparison'],
                     source = row['source'], target = row['target'], detailed_type = dtype)
            session.add(e)
        print('Links added to session')

    except Exception as e:
        session.rollback() 
        print('Unable to populate tables\n', repr(e))
    else:
        session.commit() #commit only onces: doesnt make sense to commit separately for nodes and links
        print('Tables populated')

if __name__ == '__main__':
    main()
    # data_for_students()


# def data_for_students():
#     cwd = Path(__file__).parent.resolve()
#     try:
#         ccc = pd.read_csv(cwd / 'data' / 'CCC.csv') # CCI results
#         tfl = pd.read_csv(cwd / 'data' / 'TFL.csv') #TF activity results
#     except Exception as e:
#         print('Unable to access csv file', repr(e))
#         sys.exit(1)
#     print('CSV files successfully loaded')

#     if Path.exists(cwd / 'data' / 'sanitizeCelltypes.csv'):
#         from .utils import sanitizeCelltypes
#         ccc, tfl = sanitizeCelltypes(ccc, tfl, ref_file = cwd / 'data' / 'sanitizeCelltypes.csv')
    
#     ccc_celltypes = set(ccc['sender']).union(set(ccc['receiver']))
#     tfl_celltypes = set(tfl['cellType'])

#     if ccc_celltypes.difference(tfl_celltypes):
#         print('Warning: cell types in CCC and TFL results do not match')
#         sys.exit(1)
    
#     tf_db = dc.get_collectri(organism = ORGANISM, split_complexes = SPLIT_COMPLEXES)

#     print('CCC shape:', ccc.shape)
#     ccc_filtered = ccc[ccc['pvalue_adj_S_inter'] < 0.05] 
#     print('CCC shape after filtering:', ccc_filtered.shape)

#     print('\nTESTTING')
#     print('CCC sample:')
#     print(ccc_filtered.head())
#     print('\n CCC colnames:', ccc_filtered.columns)
#     print('\nTFL sample:')
#     print(tfl.head())
#     print('\nTF database sample:')
#     print(tf_db.head())

#     import os
#     nodes_filtered, links_filtered = aggregate_full_net(ccc_filtered, tfl, tf_db, conditions = CONDS, cond_colname = TF_COND_COLNAME)
#     links_filtered = links_filtered.drop(columns=['significance'])
#     students_data = expand_links_dataframe(links_filtered)
#     students_data.to_csv(os.path.join(cwd, 'data', 'students_data_filtered.tsv'), sep="\t", index=False)
#     print('shape data for students filtered:', students_data.shape)

#     nodes, links = aggregate_full_net(ccc, tfl, tf_db, conditions = CONDS, cond_colname = TF_COND_COLNAME)
#     links = links.drop(columns=['significance'])
#     students_data = expand_links_dataframe(links)
#     students_data.to_csv(os.path.join(cwd, 'data', 'students_data.tsv'), sep="\t", index=False)

#     print('shape data for students:', students_data.shape)
    
    # print('\nAggregated nodes sample:')
    # print(nodes_filtered.head())
    # print('\nAggregated links sample:')
    # print(links_filtered.head())
    # print('\n nodes shape:', nodes_filtered.shape)
    # print('\n links shape:', links_filtered.shape)

    # print('\nChecking for cycles in the graph...')
    # cycles = find_cycles(links_filtered[['from','to', 'type']])
    # print(f'Cycles detected: {len(cycles)}')
    # for i, cycle in enumerate(cycles):
    #     print(f'Cycle {i+1}: {" -> ".join(cycle)}')


#upstream analyses settings, will have to be passed by user
# ORGANISM = 'mouse'
# SPLIT_COMPLEXES = False
# CONDS = ['Ko', 'Wt']
# TF_COND_COLNAME = 'Genotype'
# def old_main():
#     cwd = Path(__file__).parent.resolve()
#     try:
#         ccc = pd.read_csv(cwd / 'data' / 'CCC.csv') # CCI results
#         tfl = pd.read_csv(cwd / 'data' / 'TFL.csv') #TF activity results
#     except Exception as e:
#         print('Unable to access csv file', repr(e))
#         sys.exit(1)
#     print('CSV files successfully loaded')

#     if Path.exists(cwd / 'data' / 'sanitizeCelltypes.csv'):
#         from .utils import sanitizeCelltypes
#         ccc, tfl = sanitizeCelltypes(ccc, tfl, ref_file = cwd / 'data' / 'sanitizeCelltypes.csv')
    
#     ccc_celltypes = set(ccc['sender']).union(set(ccc['receiver']))
#     tfl_celltypes = set(tfl['cellType'])

#     if ccc_celltypes.difference(tfl_celltypes):
#         print('Warning: cell types in CCC and TFL results do not match')
#         sys.exit(1)
    
#     tf_db = dc.get_collectri(organism = ORGANISM, split_complexes = SPLIT_COMPLEXES)
#     nodes, links = aggregate_full_net(ccc, tfl, tf_db, conditions = CONDS, cond_colname = TF_COND_COLNAME)

#     #NaN from pandas or numpy cannot be serialized, causing Internal Server Errors
#     links = links.replace({np.nan: None})
#     nodes = nodes.replace({np.nan: None})

#     #create db engine
#     try:
#         engine = create_engine(DB_URL, echo=True) 
#         print('Database engine created')
#     except Exception as e:
#         print('Unable to access database', repr(e))
#         sys.exit(1)
    
#     # delete old tables #not sure if this is necessary
#     Base.metadata.drop_all(engine, tables=[Base.metadata.tables["nodes"], Base.metadata.tables["links"]])
#     # Create new tables
#     Base.metadata.create_all(engine)
#     print('Tables created (if not already present)')

#     #populate tables
#     session = Session(engine)
#     print('Session created')

#     try: 
#         #iterate through dataframes and add to session
#         #ids are automatically generated by sqlalchemy, with autoincrement
#         print('\nPopulating tables...')
#         for i,row in nodes.iterrows():
#             v = Node(name=row['name'], celltype=row['celltype'], moltype=row['moltype'], intrascore=row['intrascore'], verbose_id = f"{row['name']}__{row['celltype']}__{row['moltype']}")
#             session.add(v)
#         try:
#             session.flush() #this creates ids
#             print('Vertices added to session')
#         except Exception as e:
#             session.rollback()
#             raise ValueError('Unable to flush session after adding nodes\n', repr(e))
        
#         db_nodes = session.query(Node).all() 
#         print(f'Number of nodes in db: {len(db_nodes)}')
#         print(f'Number of nodes in dataframe: {len(nodes.index)}')
#         node_map = { f"{n.name}__{n.celltype}__{n.moltype}": n.id for n in db_nodes }
#         print('Node map created')

#         links['source'] = links['from'].map(node_map)
#         links['target'] = links['to'].map(node_map)
#         print('Links mapped to nodes ids')

#         for i, row in links.iterrows():
#             if row['type'] == 'TFL':
#                 if row['weight'] > 0:
#                     dtype = 'TF promotes expression of target ligand-encoding gene'
#                 else:
#                     dtype = 'TF inhibits expression of target ligand-encoding gene'
#             else:
#                 dtype = row['type']

#             e = Link(type=row['type'], weight=row['weight'], significance=row['significance'], layer=row['layer'], source = row['source'], target = row['target'], detailed_type = dtype)
#             session.add(e)
#         print('Links added to session')

#     except Exception as e:
#         session.rollback() 
#         print('Unable to populate tables\n', repr(e))
#     else:
#         session.commit() #commit only onces: doesnt make sense to commit separately for nodes and links
#         print('Tables populated')
