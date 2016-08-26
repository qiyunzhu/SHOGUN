#!/usr/bin/env python
import click
from collections import Counter
import os
import pandas as pd
from cytoolz import valmap, valfilter

from ninja_utils.utils import find_between
from ninja_utils.utils import verify_make_dir

from ninja_dojo.taxonomy import NCBITree

from ninja_shogun.wrappers import bowtie2_align
from ninja_shogun.parsers import yield_alignments_from_sam_inf


@click.command()
@click.option('-i', '--input', type=click.Path(), default=os.getcwd(), help='Directory containing the input FASTA files with ".fna" extensions (default=cwd)')
@click.option('-o', '--output', type=click.Path(), default=os.getcwd(), help='Output directory for the results')
@click.option('-b', '--bt2_indx', help='Path to the bowtie2 index')
@click.option('-x', '--extract_ncbi_tid', default='ncbi_tid|,|', help='Characters that sandwich the NCBI TID in the reference FASTA (default="ncbi_tid|,|")')
@click.option('-d', '--depth', type=click.INT, default=7, help='The depth of the search (7=species default, 0=No Collapse)')
@click.option('-p', '--threads', type=click.INT, default=1, help='The number of threads to use (default=1)')
@click.option('-a', '--annotate_lineage', type=click.BOOL, default=True, help='Annotate the NCBI Taxonomy ID with lineage (default=True)')
def shogun_bt2_lca(input, output, bt2_indx, extract_ncbi_tid, depth, threads, annotate_lineage):
    verify_make_dir(output)

    fna_files = [os.path.join(input, filename) for filename in os.listdir(input) if filename.endswith('.fna')]

    for fna_file in fna_files:
        sam_outf = os.path.join(output, '.'.join(str(os.path.basename(fna_file)).split('.')[:-1]) + '.sam')
        if os.path.isfile(sam_outf):
            print("Found the samfile <%s>. Skipping the alignment phase." % sam_outf)
        else:
            print(bowtie2_align(fna_file, sam_outf, bt2_indx, num_threads=threads))

    tree = NCBITree()
    rank_name = list(tree.mp_ranks.keys())[depth]
    if not rank_name:
        raise ValueError('Depth must be between 0 and 7, it was %d' % depth)        

    begin, end = extract_ncbi_tid.split(',')

    counts = []
    sam_files = [os.path.join(output, filename) for filename in os.listdir(output) if filename.endswith('.sam')]

    for sam_file in sam_files:
        lca_map = {}
        for qname, rname in yield_alignments_from_sam_inf(sam_file):
            ncbi_tid = int(find_between(rname, begin, end))
            if qname in lca_map:
                current_ncbi_tid = lca_map[qname]
                if current_ncbi_tid:
                    if current_ncbi_tid != ncbi_tid:
                        lca_map[qname] = tree.lowest_common_ancestor(ncbi_tid, current_ncbi_tid)
            else:
                lca_map[qname] = ncbi_tid

        if annotate_lineage:
            lca_map = valmap(lambda x: tree.green_genes_lineage(x, depth=depth), lca_map)
            taxon_counts = Counter(filter(None, lca_map.values()))
        else:
            lca_map = valfilter(lambda x: tree.get_rank_from_taxon_id(x) == rank_name, lca_map)
            taxon_counts = Counter(filter(None, lca_map.values()))
        counts.append(taxon_counts)

    df = pd.DataFrame(counts, index=['#' + '.'.join(os.path.basename(sample).split('.')[:-1]) for sample in sam_files])
    df.T.to_csv(os.path.join(output, 'taxon_counts.csv'))


if __name__ == '__main__':
    shogun_bt2_lca()
